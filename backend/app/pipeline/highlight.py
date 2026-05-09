"""高光时刻检测（运动专属）。

融合三类信号：
1) sport-specific CLIP 评分（主力）：把每个关键帧与「该运动的高光描述」做相似度，
   再减去与「无聊画面」的相似度，得到 0~1 的运动相关高光分数；
2) 主体尺度：YOLO 主体框越大（人/球离镜头近）戏剧性通常越强；
3) 帧差运动量：作为一个轻量补充。

VLM（如有 API key）作为最高优先级覆盖。

同时为每个 frame 记录"画面短语"（CLIP top prompt 的中文化），后续供文案模块使用。
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PIL import Image

from ..config import settings
from .detector import Detection
from .frames import Frame
from .sport_profiles import get_profile

log = logging.getLogger(__name__)


# CLIP 高光 prompt（英文）→ 中文短语（用于文案/UI 解释）
_PHRASE_EN_TO_CN = {
    # 滑雪
    "a skier carving a sharp turn with snow spray flying off the edges": "立刃切弯，雪粉炸开",
    "a skier launching off a kicker into the air": "起跳腾空那一下",
    "a skier landing a jump cleanly on snow": "落地干净稳压",
    "a skier blasting through deep powder with a face shot": "深雪打浪糊一脸",
    "a skier weaving through trees at high speed": "树林里钻线",
    "a wipeout / fall on a snowy slope": "摔了一跤但很有戏",
    # 单板
    "a snowboarder carving a deep heelside or toeside turn with snow spray": "压住板刃刷一刀",
    "a snowboarder launching off a jump and grabbing the board mid-air": "起跳抓板",
    "a snowboarder landing a trick on a snowy slope": "动作落地",
    "a snowboarder riding through deep powder snow": "深雪自由推进",
    "a snowboarder hitting a rail or box in a terrain park": "上 box 滑过",
    "a snowboarder wiping out / falling": "翻车现场",
    # 攀岩
    "a climber making a long dynamic move / dyno reaching for a hold": "飞身 dyno",
    "a climber on a steep overhang clipping a quickdraw": "仰角线挂快挂",
    "a climber matching feet on a tiny crimp under tension": "小点上换脚",
    "a climber topping out at the summit, both hands on the final hold": "顶上 last move",
    "a climber falling and being caught by the rope": "掉点被绳接住",
    "a climber chalking up before a hard move": "开难点前补镁粉",
    # 抱石
    "a boulderer making a dynamic jump between holds in an indoor gym": "飞点完成",
    "a boulderer holding a tense lock-off position on colored holds": "锁死那一秒",
    "a boulderer topping out a boulder problem with both hands on top": "顶上 send",
    "a boulderer falling onto crash pads": "掉到垫子上",
    "a boulderer pressing into a heel hook on an overhang": "挂跟挂稳",
    # 篮球
    "a basketball player jumping up to dunk the ball through the hoop": "扣篮一记",
    "a basketball player shooting a three pointer with proper form": "三分出手",
    "a basketball player driving past a defender to the basket": "突破上篮",
    "a basketball player making a behind the back or crossover dribble": "变向晃开",
    "a basketball player blocking a shot at the rim": "盖帽",
    "a basketball going through the net (made shot)": "球进了",
    # 足球
    "a soccer player striking the ball with power towards the goal": "重炮射门",
    "a soccer player dribbling past a defender": "过人",
    "a goalkeeper diving to make a save": "门将鱼跃扑救",
    "a soccer ball going into the net (goal)": "进球瞬间",
    "a header attempt during a soccer match": "头球争顶",
    # 网球
    "a tennis player hitting a powerful forehand winner": "正手抽击 winner",
    "a tennis player serving aggressively": "上旋发球",
    "a tennis player diving to reach a difficult shot": "鱼跃救球",
    "a tennis ball just clipping the line": "压线球",
    # 跑步
    "a runner crossing a finish line with arms up": "冲线那一下",
    "a runner sprinting at full speed on a track": "全力冲刺",
    "a runner running uphill with effort visible": "上坡咬牙顶",
    "a close up of running shoes hitting the ground": "步频特写",
    # 马拉松
    "a marathon finish line with runners crossing": "终点拱门",
    "a runner overtaking other runners on a city street": "超人一波",
    "many marathon runners packed on a road": "赛道人潮",
    "spectators cheering for marathon runners": "观众加油",
    # 骑行
    "a cyclist going downhill at high speed": "下坡贴肚皮",
    "a cyclist climbing a steep mountain road, out of the saddle": "摇车上坡",
    "a peloton of cyclists riding close together": "集团内卷",
    "a mountain biker jumping off a small drop": "小跳台落地",
    # 冲浪
    "a surfer riding inside the barrel of a wave": "管浪里",
    "a surfer carving a top turn with spray": "顶端 cutback",
    "a surfer dropping into a steep wave": "陡浪 take off",
    "a surfer wiping out in white water": "翻车浪花里",
    # 滑板
    "a skateboarder doing a kickflip on the ground": "kickflip 落地",
    "a skateboarder grinding on a rail or ledge": "杆上 grind",
    "a skateboarder dropping into a bowl or ramp": "drop in",
    "a skateboarder bailing / falling off the board": "翻车了",
    # 瑜伽
    "a person holding a difficult yoga pose like crow or handstand": "难度体式定住",
    "a person flowing through sun salutation": "拜日式串联",
    "a person in a deep backbend on a yoga mat": "深后弯",
    # 拳击
    "a boxer landing a clean cross or hook on a heavy bag or opponent": "直拳/勾拳干净命中",
    "a boxer slipping a punch and countering": "闪躲反击",
    "two boxers in a clinch in the ring": "贴身缠斗",
    "a knockdown in a boxing match": "击倒",
}


@dataclass
class HighlightScore:
    frame: Frame
    score: float        # 0~1
    reason: str         # 给 UI 显示的原因
    phrase_cn: str = ""  # 给文案用的画面短语（如"立刃切弯，雪粉炸开"）


def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _score_via_vlm(detections: List[Detection], sport: str) -> Optional[List[HighlightScore]]:
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("openai sdk unavailable: %s", exc)
        return None

    out: List[HighlightScore] = []
    profile = get_profile(sport)
    looking_for = "、".join(profile["actions"][:6]) or "该运动的关键动作"
    sys_prompt = (
        "你是体育视频高光剪辑师。看一张关键帧，输出严格 JSON："
        '{"score": 0~1, "phrase": "画面里在做什么的中文短语，10字以内", "reason": "一句话理由"}。'
        "score 评估它作为高光的价值（动作幅度大/动态强/有标志性瞬间=高，静止/远景/空场=低）。"
    )
    for d in detections:
        try:
            b64 = _encode_image(d.frame.image_path)
            resp = client.chat.completions.create(
                model=settings.openai_vision_model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text",
                             "text": f"运动：{sport}。重点关注：{looking_for}。请评估这一帧。"},
                            {"type": "image_url",
                             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=150,
            )
            text = resp.choices[0].message.content or "{}"
            data = json.loads(text)
            score = float(data.get("score", 0.0))
            phrase = str(data.get("phrase", "")).strip()
            reason = str(data.get("reason", "")) or "VLM 判定"
        except Exception as exc:  # noqa: BLE001
            log.warning("vlm score failed @ %s: %s", d.frame.image_path, exc)
            score, phrase, reason = 0.0, "", "VLM 调用失败"
        out.append(HighlightScore(
            frame=d.frame,
            score=max(0.0, min(1.0, score)),
            reason=reason,
            phrase_cn=phrase,
        ))
    return out


def _max_subject_area(d: Detection) -> float:
    """返回最大主体框面积占图比例（0~1，假设 1920×1080）。"""
    area = 0.0
    for o in d.objects:
        box = o.get("box") or [0, 0, 0, 0]
        w = max(0.0, box[2] - box[0])
        h = max(0.0, box[3] - box[1])
        area = max(area, (w * h) / (1920 * 1080))
    return min(1.0, area * 4)  # 占图 25% 以上就归一为 1



def _score_via_clip(
    detections: List[Detection], sport: str
) -> Optional[List[Tuple[float, str]]]:
    """对每帧返回 (sport_specific_score, top_phrase_cn)；CLIP 不可用则返回 None。"""
    try:
        from .classifier import get_clip_context

        ctx = get_clip_context()
    except Exception as exc:  # noqa: BLE001
        log.warning("clip ctx unavailable: %s", exc)
        return None
    if ctx is None:
        return None
    model, preprocess, _, torch = ctx

    profile = get_profile(sport)
    pos_prompts = profile["highlight_prompts"]
    neg_prompts = profile["boring_prompts"]
    if not pos_prompts:
        return None

    import open_clip

    tokenizer = open_clip.get_tokenizer("ViT-B-32-quickgelu")
    with torch.no_grad():
        pos_tok = tokenizer(pos_prompts)
        pos_feat = model.encode_text(pos_tok)
        pos_feat = pos_feat / pos_feat.norm(dim=-1, keepdim=True)
        if neg_prompts:
            neg_tok = tokenizer(neg_prompts)
            neg_feat = model.encode_text(neg_tok)
            neg_feat = neg_feat / neg_feat.norm(dim=-1, keepdim=True)
        else:
            neg_feat = None

        results: List[Tuple[float, str]] = []
        for d in detections:
            try:
                img = Image.open(d.frame.image_path).convert("RGB")
                img_t = preprocess(img).unsqueeze(0)
                img_feat = model.encode_image(img_t)
                img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
                pos_sims = (100.0 * img_feat @ pos_feat.T).softmax(dim=-1).squeeze(0)
                pos_max = float(pos_sims.max().item())
                pos_top_idx = int(pos_sims.argmax().item())
                top_en = pos_prompts[pos_top_idx]
                top_cn = _PHRASE_EN_TO_CN.get(top_en, "高光画面")
                # 负向参考：相似度高说明很无聊，对总分扣分
                neg_max = 0.0
                if neg_feat is not None:
                    neg_sims = (100.0 * img_feat @ neg_feat.T).softmax(dim=-1).squeeze(0)
                    neg_max = float(neg_sims.max().item())
                # 把 softmax 结果映射成相对得分（pos_max 通常 0.3~0.95，neg_max 类似）
                # 用差值并放到 0~1 范围
                raw = pos_max - 0.6 * neg_max
                # 因为是单独 softmax，pos_max 本身可能很高，做线性拉伸
                clip_score = max(0.0, min(1.0, (raw - 0.05) * 1.6))
                results.append((clip_score, top_cn))
            except Exception as exc:  # noqa: BLE001
                log.warning("clip score failed @ %s: %s", d.frame.image_path, exc)
                results.append((0.0, ""))
    return results


def _score_local(detections: List[Detection], sport: str) -> List[HighlightScore]:
    """本地融合评分：
    - clip_sport（运动专属高光相似度）权重 0.6（CLIP 可用时）；
    - 主体尺度 0.2（人/球离镜头近）；
    - 帧差 0.2（动作幅度）；
    CLIP 不可用时退化成 主体 0.4 + 帧差 0.6。
    """
    clip_results = _score_via_clip(detections, sport)
    out: List[HighlightScore] = []
    for i, d in enumerate(detections):
        motion = min(1.0, d.frame.motion * 4.0)
        scale = _max_subject_area(d)
        if clip_results is not None:
            clip_score, phrase = clip_results[i]
            score = 0.6 * clip_score + 0.2 * scale + 0.2 * motion
            reason_bits = []
            if phrase:
                reason_bits.append(phrase)
            if scale > 0.4:
                reason_bits.append("主体大")
            if motion > 0.3:
                reason_bits.append(f"动作({motion:.2f})")
            reason = "·".join(reason_bits) if reason_bits else "常规画面"
        else:
            score = 0.4 * scale + 0.6 * motion
            phrase = ""
            top = max(d.objects, key=lambda o: float(o.get("conf", 0))) if d.objects else None
            reason = (f"动作({motion:.2f})" + (f" 主体: {top.get('name')}" if top else "")).strip()
            if not reason:
                reason = "常规画面"
        out.append(HighlightScore(
            frame=d.frame,
            score=score,
            reason=reason,
            phrase_cn=phrase,
        ))
    return out


def score_frames(detections: List[Detection], sport: str) -> List[HighlightScore]:
    via_vlm = _score_via_vlm(detections, sport)
    if via_vlm is not None:
        return via_vlm
    return _score_local(detections, sport)


def pick_highlights(
    scores: List[HighlightScore],
    clip_duration: float,
    max_clips: int,
) -> List[dict]:
    """从打分结果挑出 top-N 高光时刻并合并临近片段。

    返回片段列表：[{src, start, end, score, reason}]
    """
    if not scores:
        return []
    # 按分数降序，取 max_clips * 2 候选，再按时间 dedupe
    cand = sorted(scores, key=lambda s: s.score, reverse=True)[: max_clips * 2]
    picked: List[dict] = []
    for s in cand:
        start = max(0.0, s.frame.timestamp - clip_duration / 2)
        end = start + clip_duration
        # 与已选片段去重（同源且时间区间重叠则跳过）
        overlap = False
        for p in picked:
            if p["src"] == s.frame.src and not (end <= p["start"] or start >= p["end"]):
                overlap = True
                break
        if overlap:
            continue
        picked.append({
            "src": s.frame.src,
            "start": round(start, 3),
            "end": round(end, 3),
            "score": round(s.score, 3),
            "reason": s.reason,
            "phrase": s.phrase_cn,
            "image_path": s.frame.image_path,
        })
        if len(picked) >= max_clips:
            break
    # 按时间顺序排序成片更连贯
    picked.sort(key=lambda p: (p["src"], p["start"]))
    return picked
