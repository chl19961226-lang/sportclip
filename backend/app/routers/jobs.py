"""任务相关路由：创建 / 查询。"""
from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..config import settings
from ..pipeline.runner import run_pipeline
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
):
    """创建任务。支持单个 file 或多文件 files。"""
    uploads: List[UploadFile] = []
    if files:
        uploads.extend(files)
    if file:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail="请上传至少一个视频文件")

    # 关键字可能以单个 form-field 多值，也可能逗号分隔
    flat_kws: List[str] = []
    for kw in keywords:
        flat_kws.extend([s.strip() for s in kw.split(",") if s.strip()])

    job = store.create(sources=[], keywords=flat_kws, style=style)
    saved = _save_uploads(job.id, uploads)
    if not saved:
        raise HTTPException(status_code=400, detail="上传文件无效")
    store.update(job.id, sources=saved)

    # 用线程而非 BackgroundTasks，避免阻塞事件循环（YOLO 推理是 CPU 密集型）
    threading.Thread(target=_execute, args=(job.id,), daemon=True).start()
    return job.to_dict()


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_dict()
