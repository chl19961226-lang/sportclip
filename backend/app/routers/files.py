"""文件下载路由：高光视频 / 缩略图。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..tasks import store

router = APIRouter()


@router.get("/files/{job_id}/highlight")
def download_highlight(job_id: str):
    job = store.get(job_id)
    if not job or not job.output_video:
        raise HTTPException(status_code=404, detail="highlight not ready")
    p = Path(job.output_video)
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing")
    return FileResponse(p, media_type="video/mp4", filename=f"highlight_{job_id}.mp4")


@router.get("/files/{job_id}/thumbnail")
def download_thumbnail(job_id: str):
    job = store.get(job_id)
    if not job or not job.thumbnail:
        raise HTTPException(status_code=404, detail="thumbnail not ready")
    p = Path(job.thumbnail)
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing")
    return FileResponse(p, media_type="image/jpeg")
