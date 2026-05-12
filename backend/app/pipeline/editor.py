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
import os
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


# ============================ 合集模式 ============================ #
# 苹果风的中性"片头/片尾"卡片：渐变底 + 大字 + 细描线 + 淡入淡出
# 使用 PIL 渲染 PNG（中文友好），再 ffmpeg 把图变成短视频（带 Ken Burns 微推近）。


def _find_cjk_font(size: int) -> "object":
    """挑一个能渲染中文 + 英文的字体。"""
    from PIL import ImageFont

    candidates = [
        # macOS
        ("/System/Library/Fonts/PingFang.ttc", 2),
        ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 1),
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
        # Linux fallback
        ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ]
    for path, idx in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size, index=idx)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _render_title_png(
    title: str,
    subtitle: str,
    out_png: Path,
    size: Tuple[int, int] = (1280, 720),
) -> Path:
    """生成"5.7 滑雪集锦"片头 PNG：墨色渐变背景 + 巨大主标题 + 细描副标题。"""
    from PIL import Image, ImageDraw, ImageFilter

    W, H = size
    img = Image.new("RGB", (W, H), color=(8, 9, 14))

    # 顶/底各放一个柔光晕（蓝+品红），模拟"光泽感"
    halo = Image.new("RGB", (W, H), color=(8, 9, 14))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([-200, -300, W // 2 + 200, 380], fill=(60, 80, 200))
    hd.ellipse([W // 2 - 200, H - 320, W + 200, H + 200], fill=(180, 60, 120))
    halo = halo.filter(ImageFilter.GaussianBlur(160))
    img = Image.blend(img, halo, 0.55)

    draw = ImageDraw.Draw(img)
    # 顶部细线 + 副标签
    top_label = (subtitle or "HIGHLIGHTS").upper()
    f_label = _find_cjk_font(24)
    f_main = _find_cjk_font(120)
    f_kicker = _find_cjk_font(28)

    # tracking: 用空格制造字距感
    tracked = " ".join(list(top_label))
    bbox = draw.textbbox((0, 0), tracked, font=f_label)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, 90), tracked, fill=(220, 220, 230), font=f_label)
    # 细线
    line_w = 60
    draw.rectangle([W / 2 - line_w / 2, 134, W / 2 + line_w / 2, 136], fill=(230, 230, 240))

    # 主标题
    bbox = draw.textbbox((0, 0), title, font=f_main)
    mw, mh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - mw) / 2, (H - mh) / 2 - 10), title, fill=(255, 255, 255), font=f_main)

    # 底部 kicker
    bottom = "CRUX · 高光剪辑师"
    bbox = draw.textbbox((0, 0), bottom, font=f_kicker)
    bw = bbox[2] - bbox[0]
    draw.text(((W - bw) / 2, H - 90), bottom, fill=(200, 200, 210), font=f_kicker)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, format="PNG")
    return out_png


def make_title_card(
    title: str,
    subtitle: str,
    out_path: Path,
    duration: float = 3.5,
    fps: int = 30,
) -> Path:
    """生成一段 ~3.5s 的标题卡 mp4。微 Ken Burns + 首尾淡入淡出。"""
    ff = _check_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    png = out_path.with_suffix(".png")
    _render_title_png(title, subtitle, png)
    total_frames = max(15, int(duration * fps))
    # zoompan d 必须 ≥ 2；用 1.0 → 1.06 的微推近
    vf = (
        f"zoompan=z='min(zoom+0.0008,1.06)':d={total_frames}:s=1280x720:fps={fps},"
        f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(0.0, duration - 0.5):.3f}:d=0.5,"
        f"setsar=1,format=yuv420p"
    )
    # 加一路静音音轨保证后续 acrossfade 不掉链
    cmd = [
        ff, "-y",
        "-loop", "1", "-t", f"{duration:.3f}", "-i", str(png),
        "-f", "lavfi", "-t", f"{duration:.3f}",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
    _run(cmd)
    return out_path


def build_compilation_video(
    clips_meta: List[dict],
    work_dir: Path,
    title: str,
    subtitle: str,
) -> Tuple[Path, Path]:
    """合集模式：标题卡 → 多段 xfade → 收尾。返回 (compilation.mp4, thumbnail.jpg)。

    `clips_meta` 已按时间顺序排好，每条 dict 含 src/start/end，单段时长一般 5~8s。
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    clip_dir = work_dir / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)

    # 1) 切片
    clips: List[Path] = []
    for i, h in enumerate(clips_meta):
        out = clip_dir / f"clip_{i:02d}.mp4"
        try:
            clips.append(cut_clip(h["src"], h["start"], h["end"], out))
        except Exception as exc:  # noqa: BLE001
            log.warning("cut clip failed [%s %.2f-%.2f]: %s",
                        h["src"], h["start"], h["end"], exc)
    if not clips:
        raise RuntimeError("合集模式：所有片段裁剪失败")

    # 2) 标题卡
    title_card = work_dir / "title.mp4"
    try:
        make_title_card(title, subtitle, title_card, duration=3.5)
    except Exception as exc:  # noqa: BLE001
        log.warning("title card failed: %s — 跳过片头", exc)
        title_card = None

    # 3) 拼接：标题卡 + clips
    final = work_dir / "highlight.mp4"  # 复用同名，前端无需改路径
    seq = ([title_card] if title_card else []) + clips
    try:
        xfade_concat(seq, final, transition_dur=0.5, intro_fade=0.0, outro_fade=0.8)
    except Exception as exc:  # noqa: BLE001
        log.warning("xfade compilation failed, fallback concat: %s", exc)
        concat_clips(seq, final)

    # 4) 缩略图：用标题卡 PNG（如果有），否则成片中段
    thumb = work_dir / "thumbnail.jpg"
    try:
        if title_card and title_card.with_suffix(".png").exists():
            # 把 PNG 直接转 jpg 作为封面（更好看）
            ff = _check_ffmpeg()
            _run([ff, "-y", "-i", str(title_card.with_suffix(".png")),
                  "-vf", "scale=640:-2", str(thumb)])
        else:
            make_thumbnail(final, thumb, at=1.5)
    except Exception as exc:  # noqa: BLE001
        log.warning("compilation thumbnail failed: %s", exc)
    return final, thumb
