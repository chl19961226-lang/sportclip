"""任务存储与状态机。

为原型简化：纯内存 dict + 锁。生产化可替换为 Redis / DB。
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


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
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()

    def create(self, sources: List[str], keywords: List[str], style: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], sources=sources, keywords=keywords, style=style)
        with self._lock:
            self._jobs[job.id] = job
        return job

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

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.stage = "failed"
            job.error = error
            job.message = f"失败：{error}"


store = JobStore()
