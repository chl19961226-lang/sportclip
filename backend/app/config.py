"""集中读取环境变量配置。"""
from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI / 兼容接口
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_vision_model: str = "gpt-4o-mini"
    openai_text_model: str = "gpt-4o-mini"

    # 模型与流水线
    yolo_weights: str = "yolov8n.pt"
    storage_dir: str = "storage"
    sample_interval_sec: float = 1.5
    clip_duration_sec: float = 3.0
    max_clips: int = 8

    # CORS：精确来源 + 正则（用于 Windsurf Preview / 任意本地端口）
    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origin_list(self) -> List[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    @property
    def use_openai(self) -> bool:
        return bool(self.openai_api_key.strip())


settings = Settings()
