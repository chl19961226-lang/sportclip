"""ffmpeg 剪辑：抽取高光片段 → 拼接成片 + 生成封面。"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger(__name__)


def _check_ffmpeg() -> str:
    bin_ = shutil.which("ffmpeg")
    if not bin_:
        raise RuntimeError("未检测到 ffmpeg，请先安装：brew install ffmpeg")
    return bin_


def _run(cmd: list[str]) -> None:
    log.info("ffmpeg: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {res.stderr[-500:]}")


def cut_clip(src: str, start: float, end: float, out_path: Path) -> Path:
    """精确裁剪一个片段（重新编码以保证拼接时无错位）。"""
    ff = _check_ffmpeg()
    duration = max(0.1, end - start)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ff, "-y",
        "-ss", f"{start:.3f}",
        "-i", src,
        "-t", f"{duration:.3f}",
        # 统一编码，便于后续 concat
        "-vf", "scale=1280:-2:flags=bicubic,fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ]
    _run(cmd)
    return out_path


def concat_clips(clips: List[Path], out_path: Path) -> Path:
    """concat demuxer 合并已统一编码的片段。"""
    ff = _check_ffmpeg()
    if not clips:
        raise RuntimeError("没有可用的高光片段")
    list_file = out_path.parent / "concat.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.as_posix()}'\n")
    cmd = [
        ff, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    _run(cmd)
    return out_path


def make_thumbnail(video: Path, out: Path, at: float = 1.0) -> Path:
    ff = _check_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ff, "-y",
        "-ss", f"{at:.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-vf", "scale=640:-2",
        str(out),
    ]
    _run(cmd)
    return out


def build_highlight_video(
    highlights: List[dict],
    work_dir: Path,
) -> Tuple[Path, Path]:
    """剪辑并拼接高光视频，返回 (highlight.mp4, thumbnail.jpg)。"""
    work_dir.mkdir(parents=True, exist_ok=True)
    clip_dir = work_dir / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    clips: List[Path] = []
    for i, h in enumerate(highlights):
        out = clip_dir / f"clip_{i:02d}.mp4"
        try:
            clips.append(cut_clip(h["src"], h["start"], h["end"], out))
        except Exception as exc:  # noqa: BLE001
            log.warning("cut clip failed [%s %.2f-%.2f]: %s", h["src"], h["start"], h["end"], exc)
    if not clips:
        raise RuntimeError("所有高光片段裁剪失败")
    final = work_dir / "highlight.mp4"
    concat_clips(clips, final)
    thumb = work_dir / "thumbnail.jpg"
    try:
        make_thumbnail(final, thumb)
    except Exception as exc:  # noqa: BLE001
        log.warning("thumbnail failed: %s", exc)
    return final, thumb
