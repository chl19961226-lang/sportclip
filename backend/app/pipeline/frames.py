"""关键帧抽取：基于固定时间间隔 + 帧差启发式，挑出"动作显著"的帧。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class Frame:
    src: str          # 源视频路径
    index: int        # 在源视频中的帧序号
    timestamp: float  # 在源视频中的秒数
    motion: float     # 与上一采样帧的差异度（0~1）
    image_path: str   # 落盘的关键帧 JPG


def probe(video_path: str) -> Tuple[float, float, int]:
    """返回 (fps, duration, frame_count)。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    duration = n / fps if fps > 0 else 0.0
    return fps, duration, n


def extract_keyframes(
    video_path: str,
    out_dir: Path,
    interval_sec: float = 1.5,
    max_frames: int = 60,
) -> List[Frame]:
    """按 interval_sec 等距采样，并计算与上一帧的差异度。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps * interval_sec)))

    frames: List[Frame] = []
    prev_gray: np.ndarray | None = None
    idx = 0
    saved = 0
    while saved < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, img = cap.read()
        if not ok or img is None:
            break
        gray = cv2.cvtColor(cv2.resize(img, (320, 180)), cv2.COLOR_BGR2GRAY)
        motion = 0.0
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            motion = float(np.mean(diff)) / 255.0
        prev_gray = gray
        ts = idx / fps
        out_path = out_dir / f"f_{Path(video_path).stem}_{idx:08d}.jpg"
        cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frames.append(Frame(src=video_path, index=idx, timestamp=ts, motion=motion, image_path=str(out_path)))
        idx += step
        saved += 1
    cap.release()
    log.info("extracted %d keyframes from %s", len(frames), video_path)
    return frames
