"""FastAPI 入口。"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import files, jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="SportClip API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(files.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {
        "service": "sportclip",
        "use_openai": settings.use_openai,
        "yolo_weights": settings.yolo_weights,
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
