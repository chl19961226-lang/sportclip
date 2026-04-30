"""高光时刻检测。

策略：
1) 优先用 VLM（OpenAI vision）对关键帧打分 + 给出原因；
2) 没 API key 时降级为基于动作幅度（帧差）+ 检测物体数量的本地启发式。
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from ..config import settings
from .detector import Detection
from .frames import Frame

log = logging.getLogger(__name__)


@dataclass
class HighlightScore:
    frame: Frame
    score: float        # 0~1
    reason: str


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
    sys_prompt = (
        "你是一个体育视频高光剪辑师。给定一张关键帧和运动类型，"
        "请评估这一帧是否是高光瞬间（如：扣篮/三分/急停跳投、空中转体/腾空起跳、"
        "登顶/动态过人、关键动作完成）。返回严格 JSON："
        '{"score": 0~1, "reason": "中文一句话"}'
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
                            {"type": "text", "text": f"运动类型：{sport}。请评估这帧的高光程度。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=120,
            )
            text = resp.choices[0].message.content or "{}"
            data = json.loads(text)
            score = float(data.get("score", 0.0))
            reason = str(data.get("reason", "")) or "VLM 判定"
        except Exception as exc:  # noqa: BLE001
            log.warning("vlm score failed @ %s: %s", d.frame.image_path, exc)
            score, reason = 0.0, "VLM 调用失败"
        out.append(HighlightScore(frame=d.frame, score=max(0.0, min(1.0, score)), reason=reason))
    return out


def _score_local(detections: List[Detection], sport: str) -> List[HighlightScore]:
    """本地启发式：动作幅度 0.6 + 检测物体数 0.3 + 主体大小 0.1。"""
    out: List[HighlightScore] = []
    for d in detections:
        motion = min(1.0, d.frame.motion * 4.0)  # 帧差通常 < 0.25，放大
        n_obj = min(1.0, len(d.objects) / 3.0)
        # 最大主体框面积占比
        area_ratio = 0.0
        for o in d.objects:
            box = o.get("box") or [0, 0, 0, 0]
            w = max(0.0, box[2] - box[0])
            h = max(0.0, box[3] - box[1])
            area_ratio = max(area_ratio, (w * h) / (1920 * 1080))
        score = 0.6 * motion + 0.3 * n_obj + 0.1 * min(1.0, area_ratio * 4)
        reason_parts = []
        if motion > 0.3:
            reason_parts.append(f"动作幅度强({motion:.2f})")
        if d.objects:
            top = max(d.objects, key=lambda o: float(o.get("conf", 0)))
            reason_parts.append(f"主体: {top.get('name')}")
        if not reason_parts:
            reason_parts.append("常规画面")
        out.append(HighlightScore(frame=d.frame, score=score, reason="；".join(reason_parts)))
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
        })
        if len(picked) >= max_clips:
            break
    # 按时间顺序排序成片更连贯
    picked.sort(key=lambda p: (p["src"], p["start"]))
    return picked
