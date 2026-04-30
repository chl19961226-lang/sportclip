"""文案生成：根据运动类型 + 关键词 + 风格，生成标题/正文/Hashtag。"""
from __future__ import annotations

import json
import logging
import random
from typing import Dict, List

from ..config import settings

log = logging.getLogger(__name__)


STYLE_PRESETS = {
    "燃": {"tone": "热血、富有冲击力", "emoji": ["🔥", "⚡️", "💥", "🏆"]},
    "治愈": {"tone": "温柔、细腻、感性", "emoji": ["🌿", "🌅", "✨", "🤍"]},
    "搞笑": {"tone": "幽默、自嘲、网感强", "emoji": ["😂", "🤣", "🙃", "✌️"]},
    "专业": {"tone": "克制、专业、技术向", "emoji": ["🎯", "📈", "🧠", "🏅"]},
    "vlog": {"tone": "口语、生活化、有故事感", "emoji": ["📷", "🎬", "🌤️", "☁️"]},
}


def _mock_caption(sport: str, keywords: List[str], style: str) -> Dict[str, object]:
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["燃"])
    emoji = random.choice(preset["emoji"])
    kw = "、".join(keywords) if keywords else "今日训练"
    title_pool = [
        f"{emoji} 今日{sport} | {kw}",
        f"{sport}的高光时刻｜{kw} {emoji}",
        f"一镜到底的{sport}：{kw} {emoji}",
    ]
    body_pool = [
        f"今天的{sport}状态在线，把{kw}练到位的感觉太爽了。"
        f"动作幅度、出手时机、节奏掌控——一一拉满。" + emoji,
        f"为{sport}留一段值得反复看的画面。"
        f"关键词：{kw}。每一帧都是热爱在跳动。" + emoji,
        f"坚持的意义在于：你能拍到自己变好。"
        f"{sport}｜{kw}｜继续上分。" + emoji,
    ]
    hashtags = list({f"#{t}" for t in [sport, *keywords, "运动日常", "高光时刻", "Vlog"] if t})
    return {
        "title": random.choice(title_pool),
        "body": random.choice(body_pool),
        "hashtags": hashtags,
    }


def _llm_caption(sport: str, keywords: List[str], style: str) -> Dict[str, object] | None:
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("openai sdk unavailable: %s", exc)
        return None
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["燃"])
    sys = (
        "你是社交媒体运营高手，擅长写小红书 / 抖音 / Instagram 风格的运动分享文案。"
        "严格输出 JSON：{\"title\": str, \"body\": str (60-120字), \"hashtags\": [str, ...] (3-8个，每个以#开头)}。"
    )
    user = (
        f"运动类型：{sport}\n"
        f"用户关键词：{', '.join(keywords) if keywords else '无'}\n"
        f"风格基调：{style}（{preset['tone']}）\n"
        "请生成一段适合发到社交媒体的运动 vlog 文案。"
    )
    try:
        resp = client.chat.completions.create(
            model=settings.openai_text_model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.85,
            max_tokens=400,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        # 容错处理
        title = str(data.get("title", "")) or f"{sport}｜今日高光"
        body = str(data.get("body", ""))
        tags = data.get("hashtags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split() if t.strip()]
        tags = [t if str(t).startswith("#") else f"#{t}" for t in tags]
        return {"title": title, "body": body, "hashtags": tags}
    except Exception as exc:  # noqa: BLE001
        log.warning("llm caption failed: %s", exc)
        return None


def generate_caption(sport: str, keywords: List[str], style: str) -> Dict[str, object]:
    return _llm_caption(sport, keywords, style) or _mock_caption(sport, keywords, style)
