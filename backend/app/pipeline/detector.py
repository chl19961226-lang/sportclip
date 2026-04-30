"""YOLO 主体检测 + 基于检测结果的运动启发式分类。

YOLOv8n COCO 类目里直接相关的运动物体：
- 32 sports ball, 34 baseball bat, 35 baseball glove, 36 skateboard,
- 37 surfboard, 38 tennis racket, 30 skis, 31 snowboard, 33 kite

我们把这些 + person 计数后做一个简单的启发式运动分类。
攀岩 / 篮球细分等需要更强的视觉识别 → 留 hook 给 VLM 模块覆盖。
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .frames import Frame

log = logging.getLogger(__name__)

# 启发式映射：(主导物体集合) -> 运动类型
SPORT_RULES: List[Tuple[set, str]] = [
    ({"skis"}, "滑雪"),
    ({"snowboard"}, "单板滑雪"),
    ({"skateboard"}, "滑板"),
    ({"surfboard"}, "冲浪"),
    ({"tennis racket"}, "网球"),
    ({"baseball bat"}, "棒球"),
    ({"baseball glove"}, "棒球"),
    ({"sports ball"}, "球类运动"),
    ({"kite"}, "风筝冲浪"),
    ({"bicycle"}, "骑行"),
    ({"horse"}, "马术"),
]

_yolo_model = None
_yolo_failed = False


def _load_model(weights: str):
    """懒加载 YOLO 模型；失败则降级。"""
    global _yolo_model, _yolo_failed
    if _yolo_model is not None or _yolo_failed:
        return _yolo_model
    try:
        from ultralytics import YOLO  # type: ignore

        _yolo_model = YOLO(weights)
        log.info("YOLO model loaded: %s", weights)
    except Exception as exc:  # noqa: BLE001
        log.warning("YOLO unavailable (%s) — fallback to no-detection mode", exc)
        _yolo_failed = True
        _yolo_model = None
    return _yolo_model


@dataclass
class Detection:
    frame: Frame
    objects: List[Dict[str, object]]   # [{name, conf, box:[x1,y1,x2,y2]}]


def detect(frames: List[Frame], weights: str) -> List[Detection]:
    model = _load_model(weights)
    if model is None:
        return [Detection(frame=f, objects=[]) for f in frames]
    results = []
    paths = [f.image_path for f in frames]
    # ultralytics 支持批量推理
    preds = model.predict(paths, verbose=False, conf=0.25)
    for f, r in zip(frames, preds):
        objs: List[Dict[str, object]] = []
        names = r.names if hasattr(r, "names") else {}
        boxes = getattr(r, "boxes", None)
        if boxes is not None and len(boxes) > 0:
            for cls_id, conf, xyxy in zip(
                boxes.cls.tolist(), boxes.conf.tolist(), boxes.xyxy.tolist()
            ):
                objs.append({
                    "name": names.get(int(cls_id), str(int(cls_id))),
                    "conf": float(conf),
                    "box": [float(x) for x in xyxy],
                })
        results.append(Detection(frame=f, objects=objs))
    return results


def classify_sport(detections: List[Detection]) -> Tuple[str, float, Counter]:
    """根据检测物体频次推断运动类型；返回 (类型, 置信度, 频次)。"""
    counter: Counter = Counter()
    for d in detections:
        for o in d.objects:
            counter[o["name"]] += 1
    # 按规则优先匹配
    for triggers, sport in SPORT_RULES:
        if any(t in counter for t in triggers):
            score = sum(counter[t] for t in triggers if t in counter)
            confidence = min(1.0, score / max(1, len(detections)))
            return sport, confidence, counter
    # 兜底：如果检测到大量 person → 通用运动
    if counter.get("person", 0) >= max(1, len(detections) * 0.5):
        return "通用运动", 0.4, counter
    return "通用运动", 0.2, counter
