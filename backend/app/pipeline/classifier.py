"""运动类型识别（强化版）。

三层策略（自动降级）：
  1. VLM（OpenAI 兼容多模态）：给多张关键帧，让模型从候选中投票
  2. CLIP 零样本（open-clip-torch，本地）：对每帧做图文相似度，所有帧平均
  3. YOLO 启发式：基于 COCO 检测物体频次推断

相比旧版（只有 YOLO 启发式），可靠识别：
- 篮球 / 足球 / 排球 / 网球 / 乒乓球 / 羽毛球 / 棒球 / 高尔夫 / 台球
- 双板滑雪 / 单板滑雪 / 滑冰 / 冲浪 / 游泳
- 攀岩 / 抱石 / 瑜伽 / 健身房 / 举重 / 拳击 / 跆拳道
- 跑步 / 马拉松 / 骑行 / 马术 / 滑板 / 跑酷
- 跳伞 / 滑翔伞 / 蹦极 / 钓鱼 / 登山 / 皮划艇 / 体操 / 跳水 / 射箭 / 击剑 / 赛车
"""
from __future__ import annotations

import base64
import json
import logging
from typing import List, Optional, Tuple

from PIL import Image

from ..config import settings
from .detector import Detection, classify_sport as heuristic_classify
from .frames import Frame

log = logging.getLogger(__name__)


# 候选 → 英文描述（给 CLIP/VLM）。顺序对结果没有影响。
SPORT_PROMPTS = {
    "篮球": "a person playing basketball, dribbling or shooting at a basketball hoop",
    "足球": "a person playing soccer / football on a field, kicking a soccer ball",
    "网球": "a person playing tennis, hitting a tennis ball with a racket on a tennis court",
    "羽毛球": "a person playing badminton with a racket and shuttlecock",
    "乒乓球": "a person playing table tennis / ping pong at a table",
    "排球": "players playing volleyball near a net",
    "棒球": "a baseball game with a player swinging a bat",
    "高尔夫": "a person playing golf, swinging a golf club on a golf course",
    "台球": "a person playing billiards or pool with a cue stick",
    "双板滑雪": "a skier skiing downhill on snow wearing two skis",
    "单板滑雪": "a snowboarder riding down a snowy slope on a snowboard",
    "滑冰": "a person ice skating on an ice rink",
    "冲浪": "a surfer riding a wave on a surfboard in the ocean",
    "游泳": "a person swimming in a swimming pool",
    "跑步": "a person running or jogging on a road or track",
    "马拉松": "many runners in a marathon race on a city road",
    "骑行": "a person riding a bicycle, cycling or mountain biking",
    "攀岩": "a person rock climbing on a cliff or climbing wall with ropes and harness",
    "抱石": "a person bouldering, indoor climbing on a short wall without ropes, on colored holds",
    "瑜伽": "a person doing yoga poses on a yoga mat",
    "健身房训练": "a person working out in a gym with dumbbells or machines",
    "举重": "a person lifting heavy barbells, weightlifting or powerlifting",
    "拳击": "two boxers in a boxing ring wearing gloves",
    "跆拳道": "a person doing martial arts, taekwondo or karate kick",
    "马术": "a person riding a horse, equestrian sport",
    "滑板": "a person skateboarding, doing tricks on a skateboard",
    "跑酷": "a person doing parkour, jumping over urban obstacles",
    "跳伞": "a skydiver falling through the sky with a parachute",
    "滑翔伞": "a paraglider flying in the sky under a canopy",
    "蹦极": "a person bungee jumping from a high platform",
    "钓鱼": "a person fishing with a rod by water",
    "登山": "a mountaineer hiking up a snowy mountain",
    "皮划艇": "a person kayaking or canoeing on water",
    "赛车": "a racing car on a race track",
    "射箭": "an archer aiming a bow and arrow",
    "击剑": "two fencers dueling with swords",
    "体操": "a gymnast performing on the floor or apparatus",
    "跳水": "a diver jumping off a diving platform into a pool",
}

LABELS: List[str] = list(SPORT_PROMPTS.keys())
PROMPTS: List[str] = list(SPORT_PROMPTS.values())


# --------------------------------------------------------------------------- #
# CLIP 零样本（也供 highlight.py 复用，避免重复加载）                          #
# --------------------------------------------------------------------------- #
_clip_ctx = None
_clip_failed = False


def get_clip_context():
    """返回 (model, preprocess, _, torch)；highlight 模块用其中的 model/preprocess/torch。"""
    return _load_clip()


def _load_clip():
    global _clip_ctx, _clip_failed
    if _clip_ctx is not None or _clip_failed:
        return _clip_ctx
    try:
        import open_clip
        import torch

        # 使用 quickgelu 变体以与 OpenAI 原版权重激活函数完全对齐
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32-quickgelu", pretrained="openai"
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer("ViT-B-32-quickgelu")

        # 预编码文本特征（每次推理都复用）
        with torch.no_grad():
            text_tokens = tokenizer(PROMPTS)
            text_feat = model.encode_text(text_tokens)
            text_feat = text_feat / text_feat.norm(dim=-1, keepdim=True)

        _clip_ctx = (model, preprocess, text_feat, torch)
        log.info("CLIP ViT-B-32 loaded for sport classification")
    except Exception as exc:  # noqa: BLE001
        log.warning("CLIP unavailable (%s) — skip CLIP stage", exc)
        _clip_failed = True
        _clip_ctx = None
    return _clip_ctx


def _classify_via_clip(frames: List[Frame]) -> Optional[Tuple[str, float, List[Tuple[str, float]]]]:
    ctx = _load_clip()
    if ctx is None:
        return None
    model, preprocess, text_feat, torch = ctx

    # 最多用 20 张关键帧投票，避免拖慢
    sample = frames[:20]
    if not sample:
        return None

    import numpy as np

    agg: Optional["np.ndarray"] = None
    ok = 0
    with torch.no_grad():
        for f in sample:
            try:
                img = Image.open(f.image_path).convert("RGB")
            except Exception as exc:  # noqa: BLE001
                log.warning("open frame failed %s: %s", f.image_path, exc)
                continue
            img_t = preprocess(img).unsqueeze(0)
            img_feat = model.encode_image(img_t)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            # CLIP 原始 logits 用 100 温度放大，再 softmax
            sims = (100.0 * img_feat @ text_feat.T).softmax(dim=-1).squeeze(0).cpu().numpy()
            agg = sims if agg is None else agg + sims
            ok += 1

    if agg is None or ok == 0:
        return None
    agg = agg / ok
    order = agg.argsort()[::-1]
    top = [(LABELS[int(i)], float(agg[int(i)])) for i in order[:5]]
    best_label, best_score = top[0]
    log.info("CLIP sport vote (n=%d): %s", ok, top)
    return best_label, best_score, top


# --------------------------------------------------------------------------- #
# VLM（OpenAI 兼容）                                                           #
# --------------------------------------------------------------------------- #
def _classify_via_vlm(frames: List[Frame]) -> Optional[Tuple[str, float]]:
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("openai sdk unavailable: %s", exc)
        return None

    if not frames:
        return None
    # 均匀取最多 5 张关键帧
    step = max(1, len(frames) // 5)
    sample = frames[::step][:5]

    content = [
        {
            "type": "text",
            "text": (
                "请看这些来自同一段视频的关键帧，判断这是什么运动。"
                f"从以下候选中选一个最贴切的：{ '、'.join(LABELS) }。"
                "返回严格 JSON：{\"sport\": \"中文名\", \"confidence\": 0~1, \"reason\": \"一句话理由\"}"
            ),
        }
    ]
    for f in sample:
        try:
            with open(f.image_path, "rb") as fp:
                b64 = base64.b64encode(fp.read()).decode("ascii")
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("encode frame for vlm failed: %s", exc)

    try:
        resp = client.chat.completions.create(
            model=settings.openai_vision_model,
            messages=[
                {"role": "system", "content": "你是运动视频分类器。"},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=150,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        sport = str(data.get("sport", "")).strip()
        conf = float(data.get("confidence", 0.6))
        reason = str(data.get("reason", ""))
        if sport:
            log.info("VLM sport: %s (%.2f) — %s", sport, conf, reason)
            # 若返回了候选以外的项，fallback 让下一层决定
            if sport in LABELS:
                return sport, conf
            log.info("VLM returned out-of-catalog sport: %s — ignored", sport)
    except Exception as exc:  # noqa: BLE001
        log.warning("VLM classify failed: %s", exc)
    return None


# --------------------------------------------------------------------------- #
# 对外主接口                                                                   #
# --------------------------------------------------------------------------- #
def classify_sport_advanced(
    detections: List[Detection], frames: List[Frame]
) -> Tuple[str, float, str]:
    """返回 (sport, confidence, source) —— source ∈ {vlm, clip, heuristic}。"""

    # 1) VLM 优先
    vlm = _classify_via_vlm(frames)
    if vlm and vlm[1] >= 0.5:
        return vlm[0], vlm[1], "vlm"

    # 2) CLIP
    clip = _classify_via_clip(frames)

    # 3) YOLO 启发式
    h_sport, h_conf, _ = heuristic_classify(detections)

    # 综合判定：CLIP 通常比启发式更准；若 CLIP top1 明显领先则直接采信
    if clip is not None:
        top_label, top_score, top5 = clip
        # 与第二名拉开差距才认为可信
        margin = top_score - (top5[1][1] if len(top5) > 1 else 0.0)
        if top_score >= 0.30 or margin >= 0.10:
            return top_label, top_score, "clip"
        # 否则若启发式给出具体项（非"通用运动"）且置信度更高，采启发式
        if h_sport != "通用运动" and h_conf > top_score:
            return h_sport, h_conf, "heuristic"
        # 最后仍然返回 CLIP top1
        return top_label, top_score, "clip"

    return h_sport, h_conf, "heuristic"
