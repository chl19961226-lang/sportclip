"""任务存储与状态机。

数据结构：纯内存 dict + 锁，并把 jobs 持久化到 storage/jobs.json，
重启后自动 reload。`_scored_cache`（每帧的 HighlightScore 对象）由于体积大、
对象嵌套深，**不持久化**——重启后老 job 不能再用"应用并重剪"流程，
但仍可查看、拖拽排序、用作视频库素材。
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


JOB_STAGES = [
    ("queued", "排队中"),
    ("extract_frames", "抽取关键帧"),
    ("detect_subjects", "YOLO 主体检测"),
    ("classify_sport", "运动类型识别"),
    ("detect_highlights", "高光时刻检测"),
    ("edit_video", "剪辑拼接成片"),
    ("generate_caption", "生成分享文案"),
    ("done", "完成"),
    ("failed", "失败"),
]
STAGE_ORDER: Dict[str, int] = {name: i for i, (name, _) in enumerate(JOB_STAGES)}
STAGE_LABEL: Dict[str, str] = {name: label for name, label in JOB_STAGES}


@dataclass
class Job:
    id: str
    sources: List[str]                       # 上传文件的本地绝对路径
    keywords: List[str]                      # 文案关键词
    style: str                               # 文案风格：燃/治愈/搞笑/专业...
    created_at: float = field(default_factory=time.time)

    # 与 sources 对齐的源视频缩略图路径（用于"已上传视频库"展示）
    source_thumbnails: List[Optional[str]] = field(default_factory=list)

    # 模式：highlight（短高光预览）/ compilation（运动合集长片）
    mode: str = "highlight"
    title: Optional[str] = None              # 合集标题，如 "5.7 滑雪集锦"
    cover_date: Optional[str] = None         # 显示用日期字符串，如 "5.7" / "May 7"

    # 用户可在结果页调整的剪辑参数（重剪时复用）
    max_clips: int = 8                       # 短高光：总片段数
    clip_duration_sec: float = 3.0           # 单段时长（合集模式会自动放宽）
    min_score: float = 0.0                   # 0~1：低于此分数的帧不入选
    per_source_max: int = 4                  # 合集：每条源最多多少段
    total_max: int = 18                      # 合集：总段数上限
    min_per_source: int = 1                  # 合集：每条源至少入选多少段

    stage: str = "queued"
    progress: float = 0.0                    # 0~1
    message: str = ""
    error: Optional[str] = None

    # 中间产物 / 结果
    sport_type: Optional[str] = None
    sport_confidence: float = 0.0
    highlights: List[Dict[str, Any]] = field(default_factory=list)  # [{src, start, end, score, reason}]
    output_video: Optional[str] = None
    thumbnail: Optional[str] = None
    caption: Optional[Dict[str, Any]] = None  # {title, body, hashtags}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stage_label"] = STAGE_LABEL.get(self.stage, self.stage)
        # 客户端不需要绝对路径
        d.pop("sources", None)
        return d


class JobStore:
    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._jobs: Dict[str, Job] = {}
        # 流水线一次性产物（不暴露给前端）：
        # 已打分的所有候选帧 List[HighlightScore]
        # 用于"重新剪辑"时复用，避免再次跑 YOLO/CLIP/VLM。
        self._scored_cache: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._persist_path: Optional[Path] = persist_path

    # ------------------------- 持久化 ------------------------- #
    def configure_persistence(self, path: Path) -> None:
        """由调用方在 settings 加载完成后注入持久化路径，并立即 reload。"""
        self._persist_path = path
        self._load()

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            with self._persist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            log.exception("load jobs.json failed; starting fresh")
            return
        if not isinstance(data, dict) or "jobs" not in data:
            return
        valid_fields = {f.name for f in fields(Job)}
        loaded = 0
        for jd in data.get("jobs", []):
            if not isinstance(jd, dict) or "id" not in jd:
                continue
            try:
                job = Job(**{k: v for k, v in jd.items() if k in valid_fields})
            except Exception:  # noqa: BLE001
                log.exception("invalid job entry skipped: %s", jd.get("id"))
                continue
            with self._lock:
                self._jobs[job.id] = job
            loaded += 1
        log.info("jobs reloaded from %s: %d", self._persist_path, loaded)

    def _save_locked(self) -> None:
        """调用前需已持有 self._lock。"""
        if not self._persist_path:
            return
        payload = {"jobs": [asdict(j) for j in self._jobs.values()]}
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._persist_path.parent,
                prefix=".jobs_", suffix=".tmp", delete=False,
            )
            try:
                json.dump(payload, tmp, ensure_ascii=False, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
            finally:
                tmp.close()
            os.replace(tmp.name, self._persist_path)
        except Exception:  # noqa: BLE001
            log.exception("save jobs.json failed")

    def list_jobs(self) -> List[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    # ------------------------- scored frames 缓存 ------------------------- #
    def set_scored(self, job_id: str, scored: Any) -> None:
        with self._lock:
            self._scored_cache[job_id] = scored

    def get_scored(self, job_id: str) -> Any:
        with self._lock:
            return self._scored_cache.get(job_id)

    def create(
        self,
        sources: List[str],
        keywords: List[str],
        style: str,
        mode: str = "highlight",
        title: Optional[str] = None,
        cover_date: Optional[str] = None,
    ) -> Job:
        # 合集模式默认单段更长 / 总段数更多
        if mode == "compilation":
            clip_duration_sec = 6.0
            max_clips = 18
        else:
            clip_duration_sec = 3.0
            max_clips = 8
        job = Job(
            id=uuid.uuid4().hex[:12],
            sources=sources,
            keywords=keywords,
            style=style,
            mode=mode,
            title=title,
            cover_date=cover_date,
            clip_duration_sec=clip_duration_sec,
            max_clips=max_clips,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._save_locked()
        return job

    def delete(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                self._jobs.pop(job_id, None)
                self._scored_cache.pop(job_id, None)
                self._save_locked()
                return True
            return False

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            for k, v in fields.items():
                setattr(job, k, v)
            self._save_locked()
            return job

    def set_stage(self, job_id: str, stage: str, message: str = "", progress: Optional[float] = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.stage = stage
            job.message = message or STAGE_LABEL.get(stage, stage)
            if progress is not None:
                job.progress = max(0.0, min(1.0, progress))
            else:
                # 自动按阶段顺序推进进度
                idx = STAGE_ORDER.get(stage, 0)
                total = STAGE_ORDER["done"]
                if total > 0:
                    job.progress = max(job.progress, idx / total)
            self._save_locked()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.stage = "failed"
            job.error = error
            job.message = f"失败：{error}"
            self._save_locked()


store = JobStore()
