"""文案生成（小红书/Vlog 风格）。

设计目标：摆脱"加油热爱坚持"的套话，让文案能：
1) 从这条视频里挑到的高光画面里找具体材料（"立刃切弯，雪粉炸开"）；
2) 从该运动的体感词典里抽个人感受词（"雪刃啃住雪面那一下的回弹"）；
3) 把用户给的关键词自然嵌进去，而不是塞在标题最末尾；
4) 风格基调（燃 / 治愈 / 搞笑 / 专业 / vlog）影响节奏、emoji、句式；
5) 有 OpenAI key 时把 top 3 高光帧也喂给 VLM，让模型真的"看到"内容再写。

输出严格结构：title / body (90~150 字) / hashtags (5~8 个)
"""
from __future__ import annotations

import base64
import json
import logging
import random
from typing import Dict, List, Optional

from ..config import settings
from .sport_profiles import GENERIC_DEFAULT, get_profile

log = logging.getLogger(__name__)


# 风格画像：tone（语感描述）+ emoji 池 + few-shot 范文片段（给 LLM 学语感）
STYLE_PRESETS: Dict[str, Dict[str, object]] = {
    "燃": {
        "tone": "短句、节奏强、爆发力，多用动词和拟声/拟态描写，冲击感",
        "emoji": ["🔥", "⚡️", "💥", "🏆", "🤘", "🚀"],
        "demo": "脚下蹬出去那一下\n板刃啃住雪面 雪粉炸开\n风灌进面罩 心跳跟节奏咬死\n这一刀 我等了一整个雪季",
    },
    "治愈": {
        "tone": "缓、柔、感性，多用通感描写和呼吸 / 光线 / 温度的细节，留白多",
        "emoji": ["🌿", "🌅", "✨", "🤍", "🍃", "☁️"],
        "demo": "山雾还没散\n板尖一压 雪面就软软地接住我\n世界突然变得很小 只剩呼吸和雪线\n这种时刻 不忍心拍太多 只想留在身体里",
    },
    "搞笑": {
        "tone": "网感、自嘲、反差、留扣子，敢用流行梗，但要真诚不油",
        "emoji": ["😂", "🤣", "🙃", "✌️", "🤡", "🫠"],
        "demo": "教练说我立刃像在拖地\n我说没事 反正雪场空气好\n结果下一弯 雪粉糊一脸\n谢谢 我学会了",
    },
    "专业": {
        "tone": "克制、技术、术语精准，关注动作要领 / 装备 / 数据，少 emoji",
        "emoji": ["🎯", "📈", "🧠", "🏅"],
        "demo": "今天专项练立刃过渡：\n重心前移要提前半拍 髋部带板头\n过渡期手别甩 脚踝先做功\n回看视频 第三弯压刃终于干净了",
    },
    "vlog": {
        "tone": "口语、有故事感、生活化、有时间线（早上/中午/最后一缆）",
        "emoji": ["📷", "🎬", "🌤️", "☁️", "🤍"],
        "demo": "早场到顶上 雪刚压完\n刷了几趟 找到节奏\n中午被太阳晒化的雪粉是另一种触感\n最后一缆 把所有体力都花完才下山",
    },
}


# ============================ 工具函数 ============================ #
def _normalize_phrases(highlights: List[Dict]) -> List[str]:
    """从高光片段里挑出具体的画面短语，去重保序。"""
    seen: List[str] = []
    for h in highlights:
        p = (h.get("phrase") or "").strip()
        if p and p not in seen and p != "高光画面":
            seen.append(p)
    return seen[:6]


def _build_fact_card(
    sport: str,
    keywords: List[str],
    highlights: List[Dict],
) -> Dict[str, object]:
    """构造"事实卡"——视频里实际发生了什么。"""
    profile = get_profile(sport)
    phrases = _normalize_phrases(highlights)
    total_dur = sum(max(0.0, (h.get("end", 0) - h.get("start", 0))) for h in highlights)
    return {
        "sport": sport,
        "duration_sec": round(total_dur, 1),
        "clip_count": len(highlights),
        "scenes": phrases,                                 # 视觉素材
        "user_keywords": keywords,                         # 用户主观侧重
        "actions": profile["actions"],                     # 运动专属动作词
        "sensations": profile["sensations"],               # 运动专属体感词
        "gear": profile["gear"],
        "venues": profile["venues"],
        "preferred_hashtags": profile["hashtags"],
    }


# ============================ LLM 路径 ============================ #
def _llm_caption(
    sport: str,
    keywords: List[str],
    style: str,
    highlights: List[Dict],
) -> Optional[Dict[str, object]]:
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("openai sdk unavailable: %s", exc)
        return None

    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["vlog"])
    fact = _build_fact_card(sport, keywords, highlights)

    sys_prompt = (
        "你是顶级小红书运动博主，文案有 10 万+ 收藏经验。\n"
        "你的写作纪律：\n"
        "1. 必须从用户给的「画面素材 (scenes)」里挑 1~2 个具体动作/瞬间嵌入正文，让读者隔着屏幕能感到画面；\n"
        "2. 必须从「体感词典 (sensations)」里挑 1 个具体身体感受写进去（比如「雪刃啃住雪面那一下的回弹」）；\n"
        "3. 不要使用「加油」「热爱」「坚持」「燃烧」「永不放弃」「奔跑吧」「向阳而生」这类空泛口号；\n"
        "4. 不要堆 emoji，全文 emoji 不超过 4 个；\n"
        "5. 标题 ≤ 22 字，正文 90~150 字，分 2~4 段，每段一行；\n"
        "6. hashtags 5~8 个，每个以 # 开头，混用运动专属 + 用户关键词；\n"
        "7. 输出严格 JSON: {\"title\": str, \"body\": str, \"hashtags\": [str,...]}"
    )

    user_lines = [
        f"运动：{fact['sport']}",
        f"成片时长：约 {fact['duration_sec']} 秒，共 {fact['clip_count']} 段高光",
        f"画面素材 scenes（必须用上）：{ '；'.join(fact['scenes']) or '（CLIP 没识别出具体动作，请基于运动一般体验描写）'}",
        f"用户希望强调的关键词：{ '、'.join(keywords) if keywords else '无'}",
        f"风格：{style}（{preset['tone']}）",
        f"该风格的语感参考（仅学语感、不要照抄）：\n{preset['demo']}",
        f"该运动可用动作词：{ '、'.join(fact['actions'][:8]) }",
        f"该运动体感词典（请挑一句嵌入）：{ '；'.join(fact['sensations']) }",
        f"装备：{ '、'.join(fact['gear']) }；场地：{ '、'.join(fact['venues']) }",
        f"推荐 hashtags 池（可选用 / 改写）：{ ' '.join(fact['preferred_hashtags']) }",
    ]
    user_text = "\n".join(user_lines)

    # 把 top 3 高光关键帧喂给 VLM，真"看图说话"
    content: list = [{"type": "text", "text": user_text}]
    image_attached = 0
    for h in highlights[:3]:
        ip = h.get("image_path")
        if not ip:
            continue
        try:
            with open(ip, "rb") as fp:
                b64 = base64.b64encode(fp.read()).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
            image_attached += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("attach image to caption failed: %s", exc)
    if image_attached:
        content.append({
            "type": "text",
            "text": f"以上 {image_attached} 张是这条视频的高光帧，请认真看，把画面里你能看见的细节写进文案。",
        })

    try:
        resp = client.chat.completions.create(
            model=settings.openai_vision_model if image_attached else settings.openai_text_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            temperature=0.95,
            presence_penalty=0.6,
            frequency_penalty=0.3,
            max_tokens=600,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        title = str(data.get("title", "")).strip() or f"{sport}｜今日高光"
        body = str(data.get("body", "")).strip()
        tags = data.get("hashtags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split() if t.strip()]
        tags = [t if str(t).startswith("#") else f"#{t}" for t in tags if t]
        # 简单去重保序
        seen = set()
        tags = [t for t in tags if not (t in seen or seen.add(t))]
        return {"title": title, "body": body, "hashtags": tags[:8]}
    except Exception as exc:  # noqa: BLE001
        log.warning("llm caption failed: %s", exc)
        return None


# ============================ 本地兜底 ============================ #
def _mock_caption(
    sport: str,
    keywords: List[str],
    style: str,
    highlights: List[Dict],
) -> Dict[str, object]:
    """本地兜底：从画面短语 + 体感词典 + 风格池现场组合，避免每次都一样。"""
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["vlog"])
    profile = get_profile(sport)
    phrases = _normalize_phrases(highlights)
    sensations = profile["sensations"]
    actions = profile["actions"]
    venues = profile["venues"]
    hashtags_seed = profile["hashtags"]

    rng = random.Random()
    scene = rng.choice(phrases) if phrases else rng.choice(actions or ["动起来"])
    sensation = rng.choice(sensations or GENERIC_DEFAULT["sensations"])
    venue = rng.choice(venues or ["训练场"])
    emoji_pool = preset["emoji"]
    e1 = rng.choice(emoji_pool)
    e2 = rng.choice([x for x in emoji_pool if x != e1] or emoji_pool)

    # 标题模板池（按风格分支）
    if style == "燃":
        title_pool = [
            f"{e1} {scene}｜{sport} 上头瞬间",
            f"今天就为 {scene} 来这一下 {e1}",
            f"{sport}｜{scene}{e1}",
        ]
    elif style == "治愈":
        title_pool = [
            f"在{venue}里把{scene}重新过一次",
            f"{e1} 关于{sport}最安静的那段",
            f"{sport}日记｜{scene}",
        ]
    elif style == "搞笑":
        title_pool = [
            f"今天{sport}：把{scene}演成喜剧 {e1}",
            f"{sport} 翻车合集（不是）{e1}",
            f"{e1} 我的{sport}和我想的{sport}",
        ]
    elif style == "专业":
        title_pool = [
            f"{sport}专项｜{scene} 复盘",
            f"今天解决一个老问题：{scene}",
            f"{sport} 训练笔记｜{scene}",
        ]
    else:  # vlog
        title_pool = [
            f"{sport}日常｜{scene} {e1}",
            f"今天去{venue}，记一下{scene}",
            f"一段关于{sport}的小片段｜{scene}",
        ]
    title = rng.choice(title_pool)

    # 正文模板池（避免和上次一样）
    body_pool = [
        f"今天的画面里有一段我特别喜欢——{scene}。\n那种「{sensation}」在身体里走了好几秒，"
        f"后劲比想象中大。{e1}\n继续在{venue}慢慢把节奏调出来。",
        f"剪到「{scene}」的时候，自己回看了三遍。{e2}\n"
        f"是那种「{sensation}」会一下把记忆拉回当下的感觉。\n做{sport}最迷人的就是这种瞬间。",
        f"在{venue}，把今天最舒服的一下定格——{scene}。\n"
        f"{sensation}，这种感受不靠词形容，得自己去到那里才知道。{e1}",
        f"{scene}。短短一秒，但很值得反复看。\n"
        f"身体记得的是「{sensation}」——这正是我喜欢{sport}的理由。{e2}",
    ]
    body = rng.choice(body_pool)

    # hashtags 混合：用户关键词 + 运动池 + 通用
    user_tags = [f"#{k}" if not k.startswith("#") else k for k in keywords]
    pool = user_tags + hashtags_seed + ["#运动日常", "#运动vlog"]
    seen, tags = set(), []
    for t in pool:
        if t not in seen:
            seen.add(t)
            tags.append(t)
        if len(tags) >= 7:
            break

    return {"title": title, "body": body, "hashtags": tags}


# ============================ 对外接口 ============================ #
def generate_caption(
    sport: str,
    keywords: List[str],
    style: str,
    highlights: Optional[List[Dict]] = None,
) -> Dict[str, object]:
    highlights = highlights or []
    via_llm = _llm_caption(sport, keywords, style, highlights)
    if via_llm:
        return via_llm
    return _mock_caption(sport, keywords, style, highlights)
