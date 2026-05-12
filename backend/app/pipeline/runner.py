"""端到端流水线编排。"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from ..config import settings
from ..tasks import store
from .caption import generate_caption
from .classifier import classify_sport_advanced
from .detector import detect
from .editor import build_compilation_video, build_highlight_video
from .frames import Frame, extract_keyframes
from .highlight import pick_compilation_clips, pick_highlights, score_frames

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
    source_thumbnails: List[str | None] = []
    for src in job.sources:
        first_thumb: str | None = None
        try:
            frames = extract_keyframes(
                src,
                frames_dir,
                interval_sec=settings.sample_interval_sec,
                max_frames=80,
            )
            all_frames.extend(frames)
            # 每条源的第一帧用作"已上传视频库"的封面
            if frames:
                first_thumb = frames[0].image_path
        except Exception as exc:  # noqa: BLE001
            log.warning("extract frames failed for %s: %s", src, exc)
        source_thumbnails.append(first_thumb)
    if not all_frames:
        raise RuntimeError("无法从上传视频抽取任何关键帧")
    store.update(
        job_id,
        message=f"已抽取 {len(all_frames)} 帧",
        source_thumbnails=source_thumbnails,
    )

    # 2. YOLO 主体检测 --------------------------------------------------------
    store.set_stage(job_id, "detect_subjects", "YOLO 主体检测中…")
    detections = detect(all_frames, weights=settings.yolo_weights)

    # 3. 运动分类（VLM > CLIP > YOLO 启发式） --------------------------------
    store.set_stage(job_id, "classify_sport", "识别运动类型（CLIP/VLM）…")
    sport, conf, source = classify_sport_advanced(detections, all_frames)
    store.update(
        job_id,
        sport_type=sport,
        sport_confidence=round(conf, 3),
        message=f"识别为：{sport}（{source} 置信度 {conf:.2f}）",
    )

    # 4. 高光打分 -------------------------------------------------------------
    store.set_stage(job_id, "detect_highlights", "检测高光时刻…")
    scored = score_frames(detections, sport)
    # 缓存所有候选帧供"重新剪辑"复用，避免再跑一遍 YOLO/CLIP/VLM
    store.set_scored(job_id, scored)

    # 5. 挑片 + 剪辑拼接 + 文案 -----------------------------------------------
    _select_and_render(job_id, regenerate_caption=True)

    # 6. 完成 -----------------------------------------------------------------
    store.set_stage(job_id, "done", "✅ 完成", progress=1.0)
    log.info("job %s done", job_id)


# ============================ 选片 + 渲染（recut 也用） ============================ #
def _select_and_render(job_id: str, regenerate_caption: bool) -> None:
    """根据当前 job 的参数（mode/sport/title/...）和缓存的 scored 帧，挑片→剪→拼。

    被 run_pipeline 与 recut 路由共享。
    """
    job = store.get(job_id)
    if not job:
        raise RuntimeError(f"job {job_id} not found")
    scored = store.get_scored(job_id)
    if not scored:
        raise RuntimeError("缺少候选帧缓存，请重新提交任务（无法仅从结果重剪）")

    work_root = settings.storage_path / job_id
    sport = job.sport_type or "运动"
    is_compilation = (job.mode == "compilation")

    # 5.1 挑片
    store.set_stage(job_id, "detect_highlights", "重新挑选高光…")
    if is_compilation:
        highlights = pick_compilation_clips(
            scored,
            sources=job.sources,
            clip_duration=job.clip_duration_sec,
            per_source_max=job.per_source_max,
            total_max=job.total_max,
            min_per_source=job.min_per_source,
            min_score=job.min_score,
        )
        msg = f"挑出 {len(highlights)} 个合集片段（{len(job.sources)} 条素材）"
    else:
        highlights = pick_highlights(
            scored,
            clip_duration=job.clip_duration_sec,
            max_clips=job.max_clips,
            min_score=job.min_score,
        )
        msg = f"挑出 {len(highlights)} 个高光时刻"
    if not highlights:
        raise RuntimeError("当前阈值过严：未能挑出任何高光片段，请调低最低分阈值")
    store.update(job_id, highlights=highlights, message=msg)

    # 5.2 剪辑拼接
    store.set_stage(job_id, "edit_video",
                    "剪辑拼接合集片…" if is_compilation else "剪辑拼接成片…")
    if is_compilation:
        title, subtitle = _build_title_meta(job, sport)
        store.update(
            job_id,
            title=title,
            cover_date=job.cover_date or _auto_date(job.sources),
        )
        out_video, thumb = build_compilation_video(
            highlights, work_dir=work_root / "output",
            title=title, subtitle=subtitle,
        )
    else:
        out_video, thumb = build_highlight_video(
            highlights, work_dir=work_root / "output",
        )
    store.update(
        job_id,
        output_video=str(out_video),
        thumbnail=str(thumb) if Path(thumb).exists() else None,
    )

    # 5.3 文案
    if regenerate_caption:
        store.set_stage(job_id, "generate_caption", "生成分享文案…")
        caption = generate_caption(
            sport, job.keywords, job.style, highlights, mode=job.mode,
        )
        store.update(job_id, caption=caption)


# ============================ recut / recaption 入口（路由调用） ============================ #
def rerun_edit(job_id: str) -> None:
    """重新剪辑（仅挑片+剪+拼，不重新生成文案）。"""
    _select_and_render(job_id, regenerate_caption=False)
    store.set_stage(job_id, "done", "✅ 重剪完成", progress=1.0)


def rerun_with_order(job_id: str, ordered_highlights: List[dict]) -> None:
    """按用户给定的顺序（且可能删除了若干段）直接拼合，跳过 picker。

    `ordered_highlights` 必须是 job.highlights 的子集且保留 src/start/end，
    路由层负责验证 + 写入 job.highlights，本函数直接渲染。
    """
    job = store.get(job_id)
    if not job:
        raise RuntimeError(f"job {job_id} not found")
    work_root = settings.storage_path / job_id
    sport = job.sport_type or "运动"
    is_compilation = (job.mode == "compilation")

    store.set_stage(job_id, "edit_video",
                    "按你的顺序剪合集片…" if is_compilation else "按你的顺序剪成片…")
    if is_compilation:
        title, subtitle = _build_title_meta(job, sport)
        store.update(
            job_id,
            title=title,
            cover_date=job.cover_date or _auto_date(job.sources),
        )
        out_video, thumb = build_compilation_video(
            ordered_highlights, work_dir=work_root / "output",
            title=title, subtitle=subtitle,
        )
    else:
        out_video, thumb = build_highlight_video(
            ordered_highlights, work_dir=work_root / "output",
        )
    store.update(
        job_id,
        output_video=str(out_video),
        thumbnail=str(thumb) if Path(thumb).exists() else None,
    )
    store.set_stage(job_id, "done", "✅ 已按你的顺序重剪", progress=1.0)


def rerun_caption(job_id: str) -> dict:
    """仅重新生成文案。返回新 caption。"""
    job = store.get(job_id)
    if not job:
        raise RuntimeError(f"job {job_id} not found")
    if not job.highlights:
        raise RuntimeError("还没有高光片段可供生成文案")
    sport = job.sport_type or "运动"
    caption = generate_caption(
        sport, job.keywords, job.style, job.highlights, mode=job.mode,
    )
    store.update(job_id, caption=caption)
    return caption


# ============================ 合集模式辅助 ============================ #
def _auto_date(sources: List[str]) -> str:
    """从最早的源文件 mtime 推一个"5.7" 风格的中文日期。"""
    try:
        mtimes = [os.path.getmtime(s) for s in sources if os.path.exists(s)]
        if not mtimes:
            return datetime.now().strftime("%-m.%-d")
        dt = datetime.fromtimestamp(min(mtimes))
    except Exception:  # noqa: BLE001
        dt = datetime.now()
    try:
        return dt.strftime("%-m.%-d")          # macOS / linux glibc
    except Exception:  # noqa: BLE001
        return dt.strftime("%m.%d").lstrip("0").replace(".0", ".")


def _build_title_meta(job, sport: str) -> tuple[str, str]:
    """返回 (主标题, 副标签)。

    优先使用用户传入的 title；否则用 "{日期} {运动} 集锦"。
    副标签固定 "HIGHLIGHTS"（如果有 sport，就 "{sport} highlights"）。
    """
    date_str = job.cover_date or _auto_date(job.sources)
    if job.title:
        main = job.title.strip()
    else:
        main = f"{date_str} {sport}集锦"
    # 副标用英文 kicker
    subtitle = f"{sport} · HIGHLIGHTS" if sport else "HIGHLIGHTS"
    return main, subtitle
