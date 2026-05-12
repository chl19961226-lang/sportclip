"""任务相关路由：创建 / 查询。"""
from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..config import settings
from ..pipeline.runner import rerun_caption, rerun_edit, rerun_with_order, run_pipeline
from ..tasks import store

log = logging.getLogger(__name__)
router = APIRouter()


def _save_uploads(job_id: str, files: List[UploadFile]) -> List[str]:
    job_dir = settings.storage_path / job_id / "input"
    job_dir.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    for f in files:
        if not f.filename:
            continue
        # 保留原后缀，避免 ffmpeg 推断失败
        ext = Path(f.filename).suffix or ".mp4"
        dest = job_dir / f"{len(saved):02d}{ext}"
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(str(dest))
    return saved


def _execute(job_id: str) -> None:
    """后台线程：跑流水线，捕获所有异常。"""
    try:
        run_pipeline(job_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("job %s failed", job_id)
        store.fail(job_id, str(exc))


@router.post("/jobs")
async def create_job(
    background: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    keywords: List[str] = Form(default_factory=list),
    style: str = Form("燃"),
    mode: str = Form("highlight"),
    title: Optional[str] = Form(None),
    cover_date: Optional[str] = Form(None),
):
    """创建任务。支持单个 file 或多文件 files。

    mode:
      - "highlight": 短高光预览（默认，~20-40s）
      - "compilation": 运动合集长片（自动加标题片头，~90-180s）
    title / cover_date: 合集模式可选；不填则由后端按拍摄日期 + 运动自动生成。
    """
    uploads: List[UploadFile] = []
    if files:
        uploads.extend(files)
    if file:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail="请上传至少一个视频文件")
    if mode not in ("highlight", "compilation"):
        raise HTTPException(status_code=400, detail=f"不支持的 mode：{mode}")

    # 关键字可能以单个 form-field 多值，也可能逗号分隔
    flat_kws: List[str] = []
    for kw in keywords:
        flat_kws.extend([s.strip() for s in kw.split(",") if s.strip()])

    job = store.create(
        sources=[],
        keywords=flat_kws,
        style=style,
        mode=mode,
        title=(title or "").strip() or None,
        cover_date=(cover_date or "").strip() or None,
    )
    saved = _save_uploads(job.id, uploads)
    if not saved:
        raise HTTPException(status_code=400, detail="上传文件无效")
    store.update(job.id, sources=saved)

    # 用线程而非 BackgroundTasks，避免阻塞事件循环（YOLO 推理是 CPU 密集型）
    threading.Thread(target=_execute, args=(job.id,), daemon=True).start()
    return job.to_dict()


@router.get("/jobs")
def list_jobs():
    """所有任务，按创建时间倒序。用于历史记录页。"""
    return {"jobs": [j.to_dict() for j in store.list_jobs()]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_dict()


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    if not store.delete(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "id": job_id}


# ============================ 拖拽排序 / 删除片段后按当前顺序重剪 ============================ #
class ReorderItem(BaseModel):
    src: str
    start: float
    end: float


class ReorderBody(BaseModel):
    order: List[ReorderItem] = Field(default_factory=list)


def _execute_reorder(job_id: str, ordered: List[dict]) -> None:
    try:
        rerun_with_order(job_id, ordered)
    except Exception as exc:  # noqa: BLE001
        log.exception("reorder %s failed", job_id)
        store.fail(job_id, str(exc))


@router.post("/jobs/{job_id}/reorder")
def reorder_job(job_id: str, body: ReorderBody):
    """按用户给定的 highlights 顺序重新拼接，可同时删掉若干段。

    后端会做严格匹配：order 里的每条必须能在 job.highlights 里找到 (src,start,end) 等价的项；
    匹配上的高光段按 order 给定的顺序写回 job.highlights。
    """
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if not body.order:
        raise HTTPException(status_code=400, detail="order 至少要保留一段")
    if not job.highlights:
        raise HTTPException(status_code=409, detail="该任务还没有高光片段")

    def _match(it: ReorderItem) -> Optional[dict]:
        for h in job.highlights:
            if (
                h.get("src") == it.src
                and abs(float(h.get("start", -1)) - it.start) < 1e-2
                and abs(float(h.get("end", -1)) - it.end) < 1e-2
            ):
                return h
        return None

    ordered: List[dict] = []
    seen = set()
    for it in body.order:
        h = _match(it)
        if not h:
            raise HTTPException(
                status_code=400,
                detail=f"找不到对应片段：{it.src} {it.start}-{it.end}",
            )
        key = (h["src"], h["start"], h["end"])
        if key in seen:
            continue  # 去重
        seen.add(key)
        ordered.append(h)
    if not ordered:
        raise HTTPException(status_code=400, detail="排序后没有任何有效片段")

    # 写回（这就是新的 job.highlights）+ 重置进度
    store.update(job_id, highlights=ordered)
    store.set_stage(job_id, "edit_video", "按你的顺序重剪…", progress=0.5)
    threading.Thread(target=_execute_reorder, args=(job_id, ordered), daemon=True).start()
    return store.get(job_id).to_dict()


# ============================ 重新剪辑 / 重新生成文案 ============================ #
def _execute_recut(job_id: str) -> None:
    try:
        rerun_edit(job_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("recut %s failed", job_id)
        store.fail(job_id, str(exc))


@router.post("/jobs/{job_id}/recut")
async def recut_job(
    job_id: str,
    mode: Optional[str] = Form(None),
    sport_type: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    cover_date: Optional[str] = Form(None),
    max_clips: Optional[int] = Form(None),
    clip_duration_sec: Optional[float] = Form(None),
    min_score: Optional[float] = Form(None),
    per_source_max: Optional[int] = Form(None),
    total_max: Optional[int] = Form(None),
    min_per_source: Optional[int] = Form(None),
):
    """根据新的剪辑参数重新挑片 + 剪辑（不重跑 YOLO/CLIP/VLM；不重生文案）。"""
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if not store.get_scored(job_id):
        raise HTTPException(
            status_code=409,
            detail="该任务的候选帧缓存已丢失（可能服务重启过），请重新上传以再次分析。",
        )

    updates: dict = {}
    if mode is not None:
        if mode not in ("highlight", "compilation"):
            raise HTTPException(status_code=400, detail=f"不支持的 mode：{mode}")
        updates["mode"] = mode
    if sport_type is not None and sport_type.strip():
        updates["sport_type"] = sport_type.strip()
    if title is not None:
        updates["title"] = title.strip() or None
    if cover_date is not None:
        updates["cover_date"] = cover_date.strip() or None
    if max_clips is not None:
        updates["max_clips"] = max(1, min(20, int(max_clips)))
    if clip_duration_sec is not None:
        updates["clip_duration_sec"] = max(1.0, min(15.0, float(clip_duration_sec)))
    if min_score is not None:
        updates["min_score"] = max(0.0, min(0.95, float(min_score)))
    if per_source_max is not None:
        updates["per_source_max"] = max(1, min(10, int(per_source_max)))
    if total_max is not None:
        updates["total_max"] = max(2, min(40, int(total_max)))
    if min_per_source is not None:
        updates["min_per_source"] = max(0, min(3, int(min_per_source)))
    if updates:
        store.update(job_id, **updates)

    # 重置进度，让前端能看到 "重剪中"
    store.set_stage(job_id, "edit_video", "重剪中…", progress=0.5)
    threading.Thread(target=_execute_recut, args=(job_id,), daemon=True).start()
    return store.get(job_id).to_dict()


@router.post("/jobs/{job_id}/recaption")
async def recaption_job(
    job_id: str,
    style: Optional[str] = Form(None),
    keywords: List[str] = Form(default_factory=list),
    sport_type: Optional[str] = Form(None),
):
    """仅根据当前 highlights 重新生成一份文案（同步等待，最多十几秒）。"""
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.highlights:
        raise HTTPException(status_code=409, detail="还没有高光片段，无法生成文案")

    updates: dict = {}
    if style is not None and style.strip():
        updates["style"] = style.strip()
    if sport_type is not None and sport_type.strip():
        updates["sport_type"] = sport_type.strip()
    if keywords:
        flat: List[str] = []
        for kw in keywords:
            flat.extend([s.strip() for s in kw.split(",") if s.strip()])
        if flat:
            updates["keywords"] = flat
    if updates:
        store.update(job_id, **updates)

    try:
        rerun_caption(job_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("recaption %s failed", job_id)
        raise HTTPException(status_code=500, detail=str(exc))
    return store.get(job_id).to_dict()


# ============================ 已上传视频库 ============================ #
@router.get("/library")
def get_library():
    """所有 job 上传过的源视频聚合视图，按运动种类 + 月份分组。

    仅列出物理文件仍存在的素材，避免前端拿到死链。
    """
    items: List[dict] = []
    for job in store.list_jobs():
        thumbs = job.source_thumbnails or []
        for idx, src in enumerate(job.sources or []):
            try:
                if not Path(src).exists():
                    continue
            except Exception:  # noqa: BLE001
                continue
            thumb_path = thumbs[idx] if idx < len(thumbs) else None
            items.append({
                "src_id": f"{job.id}:{idx}",
                "job_id": job.id,
                "index": idx,
                "file_name": Path(src).name,
                "thumbnail_url": (
                    f"/api/files/{job.id}/source_thumb/{idx}" if thumb_path else None
                ),
                "sport_type": job.sport_type,
                "created_at": job.created_at,
                "mode": job.mode,
                "from_job_title": job.title,
            })
    return {"items": items}


# ============================ 用视频库素材合成新合集 ============================ #
class FromLibraryBody(BaseModel):
    src_ids: List[str] = Field(default_factory=list)
    mode: str = "compilation"
    title: Optional[str] = None
    cover_date: Optional[str] = None
    style: str = "vlog"
    keywords: List[str] = Field(default_factory=list)


@router.post("/jobs/from_library")
def create_job_from_library(body: FromLibraryBody):
    """直接复用历史素材路径建立新 job，不再上传文件。"""
    if not body.src_ids:
        raise HTTPException(status_code=400, detail="请选择至少 1 条素材")
    if body.mode not in ("highlight", "compilation"):
        raise HTTPException(status_code=400, detail=f"不支持的 mode：{body.mode}")

    # 解析 src_id → 真实路径，保留用户给的顺序
    sources: List[str] = []
    seen_paths: set[str] = set()
    for sid in body.src_ids:
        try:
            jid, idx_str = sid.split(":", 1)
            idx = int(idx_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"非法 src_id：{sid}")
        src_job = store.get(jid)
        if not src_job or idx < 0 or idx >= len(src_job.sources):
            raise HTTPException(status_code=404, detail=f"找不到素材：{sid}")
        path = src_job.sources[idx]
        if not Path(path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"素材文件已不存在：{Path(path).name}",
            )
        if path in seen_paths:  # 用户重复选了同一条素材，去重
            continue
        seen_paths.add(path)
        sources.append(path)

    if not sources:
        raise HTTPException(status_code=400, detail="筛选后没有可用素材")

    # 关键词扁平化
    flat_kws: List[str] = []
    for kw in body.keywords:
        flat_kws.extend([s.strip() for s in kw.split(",") if s.strip()])

    job = store.create(
        sources=sources,
        keywords=flat_kws,
        style=body.style,
        mode=body.mode,
        title=(body.title or "").strip() or None,
        cover_date=(body.cover_date or "").strip() or None,
    )
    threading.Thread(target=_execute, args=(job.id,), daemon=True).start()
    return job.to_dict()
