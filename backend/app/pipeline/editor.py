"""ffmpeg 剪辑。

输出质量考量：
- 每个高光片段重编码为统一规格（1280p / 30fps / aac），避免拼接错位；
- 拼接时用 ffmpeg 的 xfade 交叉转场（fade / fadeblack / slideleft / circleopen 等轮换）；
- 音频同步 acrossfade；若原片无音频则退化为纯视频拼接；
- 成片首尾 fade in/out。
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)


# 轮换使用的 xfade 转场样式。只选不于眼花、应用面广的几种。
XFADE_TRANSITIONS = [
    "fade",
    "fadeblack",
    "slideleft",
    "circleopen",
    "smoothleft",
    "radial",
]

# 转场时长（秒）与首尾淡入/出时长
TRANSITION_DUR = 0.45
INTRO_FADE = 0.5
OUTRO_FADE = 0.6


def _check_ffmpeg() -> str:
    bin_ = shutil.which("ffmpeg")
    if not bin_:
        raise RuntimeError("未检测到 ffmpeg，请先安装：brew install ffmpeg")
    return bin_


def _check_ffprobe() -> str:
    bin_ = shutil.which("ffprobe")
    if not bin_:
        raise RuntimeError("未检测到 ffprobe（同 ffmpeg 一起安装）")
    return bin_


def _has_audio(video: Path) -> bool:
    """使用 ffprobe 检测是否含音频流。"""
    try:
        ff = _check_ffprobe()
        res = subprocess.run(
            [ff, "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_type",
             "-of", "json", str(video)],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(res.stdout or "{}")
        return bool(data.get("streams"))
    except Exception as exc:  # noqa: BLE001
        log.warning("ffprobe audio check failed for %s: %s", video, exc)
        return False


def _probe_duration(video: Path) -> float:
    try:
        ff = _check_ffprobe()
        res = subprocess.run(
            [ff, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(video)],
            capture_output=True, text=True, timeout=10,
        )
        return float((res.stdout or "0").strip() or 0.0)
    except Exception as exc:  # noqa: BLE001
        log.warning("ffprobe duration failed for %s: %s", video, exc)
        return 0.0


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
    """concat demuxer 合并已统一编码的片段（作为 fallback）。"""
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


def xfade_concat(
    clips: List[Path],
    out_path: Path,
    transition_dur: float = TRANSITION_DUR,
    intro_fade: float = INTRO_FADE,
    outro_fade: float = OUTRO_FADE,
) -> Path:
    """使用 ffmpeg xfade 将多个片段拼接为一个带交叉转场的成片。

    转场主要是视觉上的淡化/滑入/圆扩散等；音频使用 acrossfade 同步。
    输入要求：所有 clip 已统一为 1280p / 30fps（cut_clip 已保证）。
    """
    ff = _check_ffmpeg()
    if not clips:
        raise RuntimeError("没有可用的高光片段")
    if len(clips) == 1:
        # 单片段只加首尾 fade
        return _single_clip_finalize(clips[0], out_path, intro_fade, outro_fade)

    durations = [_probe_duration(c) for c in clips]
    if any(d <= 0 for d in durations):
        log.warning("some clip has 0 duration, fallback to concat")
        return concat_clips(clips, out_path)
    if min(durations) <= transition_dur + 0.1:
        # 片段太短，压缩转场时长以避免 xfade 负偏移
        transition_dur = max(0.15, min(durations) / 3)

    use_audio = all(_has_audio(c) for c in clips)

    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]

    # 构建 filter_complex。
    # 每个输入先 setpts/asetpts 到 0，再依次 xfade / acrossfade。
    parts: list[str] = []
    for i, _ in enumerate(clips):
        parts.append(f"[{i}:v]setpts=PTS-STARTPTS,scale=1280:720:force_original_aspect_ratio=decrease,"
                     f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v{i}]")
        if use_audio:
            parts.append(f"[{i}:a]asetpts=PTS-STARTPTS,aresample=44100[a{i}]")

    # xfade 累加：offset_k = sum(durations[:k+1]) - (k+1)*transition_dur
    cum_offset = 0.0
    last_v = "v0"
    last_a = "a0" if use_audio else None
    for k in range(1, len(clips)):
        cum_offset += durations[k - 1] - transition_dur
        trans = XFADE_TRANSITIONS[(k - 1) % len(XFADE_TRANSITIONS)]
        new_v = f"vx{k}"
        parts.append(
            f"[{last_v}][v{k}]xfade=transition={trans}:"
            f"duration={transition_dur:.3f}:offset={cum_offset:.3f}[{new_v}]"
        )
        last_v = new_v
        if use_audio:
            new_a = f"ax{k}"
            parts.append(
                f"[{last_a}][a{k}]acrossfade=d={transition_dur:.3f}:c1=tri:c2=tri[{new_a}]"
            )
            last_a = new_a

    total_duration = sum(durations) - (len(clips) - 1) * transition_dur
    fade_out_st = max(0.0, total_duration - outro_fade)
    parts.append(
        f"[{last_v}]fade=t=in:st=0:d={intro_fade:.3f},"
        f"fade=t=out:st={fade_out_st:.3f}:d={outro_fade:.3f}[vout]"
    )
    if use_audio:
        parts.append(
            f"[{last_a}]afade=t=in:st=0:d={intro_fade:.3f},"
            f"afade=t=out:st={fade_out_st:.3f}:d={outro_fade:.3f}[aout]"
        )

    filter_complex = ";".join(parts)
    cmd = [ff, "-y", *inputs,
           "-filter_complex", filter_complex,
           "-map", "[vout]"]
    if use_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ]
    try:
        _run(cmd)
    except RuntimeError as exc:
        log.warning("xfade failed (%s), fallback to concat demuxer", exc)
        return concat_clips(clips, out_path)
    return out_path


def _single_clip_finalize(
    clip: Path, out_path: Path, intro_fade: float, outro_fade: float
) -> Path:
    ff = _check_ffmpeg()
    duration = _probe_duration(clip)
    fade_out_st = max(0.0, duration - outro_fade)
    use_audio = _has_audio(clip)
    vfilter = (f"fade=t=in:st=0:d={intro_fade:.3f},"
               f"fade=t=out:st={fade_out_st:.3f}:d={outro_fade:.3f}")
    cmd = [ff, "-y", "-i", str(clip), "-vf", vfilter,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-pix_fmt", "yuv420p"]
    if use_audio:
        afilter = (f"afade=t=in:st=0:d={intro_fade:.3f},"
                   f"afade=t=out:st={fade_out_st:.3f}:d={outro_fade:.3f}")
        cmd += ["-af", afilter, "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-movflags", "+faststart", str(out_path)]
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
    try:
        xfade_concat(clips, final)
    except Exception as exc:  # noqa: BLE001
        log.warning("xfade pipeline failed, fallback to plain concat: %s", exc)
        concat_clips(clips, final)
    thumb = work_dir / "thumbnail.jpg"
    try:
        make_thumbnail(final, thumb)
    except Exception as exc:  # noqa: BLE001
        log.warning("thumbnail failed: %s", exc)
    return final, thumb
