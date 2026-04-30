"""端到端流水线编排。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from ..config import settings
from ..tasks import store
from .caption import generate_caption
from .detector import classify_sport, detect
from .editor import build_highlight_video
from .frames import Frame, extract_keyframes
from .highlight import pick_highlights, score_frames

log = logging.getLogger(__name__)


def run_pipeline(job_id: str) -> None:
    job = store.get(job_id)
    if not job:
        raise RuntimeError(f"job {job_id} not found")

    work_root = settings.storage_path / job_id
    frames_dir = work_root / "frames"

    # 1. 抽取关键帧 -----------------------------------------------------------
    store.set_stage(job_id, "extract_frames", "正在抽取关键帧…")
    all_frames: List[Frame] = []
    for src in job.sources:
        try:
            frames = extract_keyframes(
                src,
                frames_dir,
                interval_sec=settings.sample_interval_sec,
                max_frames=80,
            )
            all_frames.extend(frames)
        except Exception as exc:  # noqa: BLE001
            log.warning("extract frames failed for %s: %s", src, exc)
    if not all_frames:
        raise RuntimeError("无法从上传视频抽取任何关键帧")
    store.update(job_id, message=f"已抽取 {len(all_frames)} 帧")

    # 2. YOLO 主体检测 --------------------------------------------------------
    store.set_stage(job_id, "detect_subjects", "YOLO 主体检测中…")
    detections = detect(all_frames, weights=settings.yolo_weights)

    # 3. 运动分类 -------------------------------------------------------------
    store.set_stage(job_id, "classify_sport", "识别运动类型…")
    sport, conf, _counter = classify_sport(detections)
    store.update(job_id, sport_type=sport, sport_confidence=round(conf, 3),
                 message=f"识别为：{sport}（置信度 {conf:.2f}）")

    # 4. 高光检测 -------------------------------------------------------------
    store.set_stage(job_id, "detect_highlights", "检测高光时刻…")
    scored = score_frames(detections, sport)
    highlights = pick_highlights(
        scored,
        clip_duration=settings.clip_duration_sec,
        max_clips=settings.max_clips,
    )
    if not highlights:
        raise RuntimeError("未能挑出任何高光片段")
    store.update(job_id, highlights=highlights,
                 message=f"挑出 {len(highlights)} 个高光时刻")

    # 5. 剪辑拼接 -------------------------------------------------------------
    store.set_stage(job_id, "edit_video", "剪辑拼接成片…")
    out_video, thumb = build_highlight_video(highlights, work_dir=work_root / "output")
    store.update(job_id,
                 output_video=str(out_video),
                 thumbnail=str(thumb) if Path(thumb).exists() else None)

    # 6. 文案生成 -------------------------------------------------------------
    store.set_stage(job_id, "generate_caption", "生成分享文案…")
    caption = generate_caption(sport, job.keywords, job.style)
    store.update(job_id, caption=caption)

    # 7. 完成 -----------------------------------------------------------------
    store.set_stage(job_id, "done", "✅ 完成", progress=1.0)
    log.info("job %s done", job_id)
