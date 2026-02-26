#!/usr/bin/env python3
"""
任务7：规则驱动问答 - 查询解析模块

功能：
1. 解析景区、游客类型、时长偏好
2. 抽取条件关键词
3. 输出结构化槽位
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ParsedQuery:
    """结构化查询结果"""

    raw_text: str
    scenic_spot: Optional[str] = None
    visitor_type: Optional[str] = None
    duration: Optional[str] = None
    condition_keywords: List[str] = field(default_factory=list)


_DEFAULT_INTENT_PATTERNS = {
    "scenic_spots": ["九寨沟", "故宫", "黄山"],
    "duration_patterns": {
        "two_hours": ["2小时", "两小时", "两个小时", "快速游"],
        "half_day": ["半天", "半日"],
        "one_day": ["一天", "一日", "全天", "整天"],
        "multi_day": ["两天", "2天", "三天", "3天", "多日", "几天"],
    },
    "condition_keywords": {
        "visitor": ["孩子", "小孩", "儿童", "亲子", "带娃", "老人", "情侣", "新手"],
        "route": ["路线", "顺序", "入口", "出口", "东门", "西门", "南门", "北门"],
        "time": ["早上", "上午", "中午", "下午", "晚上", "提前", "尽早", "一天", "半天", "2小时"],
        "ticketing": ["门票", "抢票", "预约", "余票", "放票"],
        "transport": ["地铁", "公交", "索道", "缆车", "步行", "观光车"],
        "weather": ["雨天", "下雨", "晴天", "雾", "雪", "天气"],
    },
}

_DEFAULT_VISITOR_TYPE_PATTERNS = {
    "family": ["孩子", "小孩", "儿童", "亲子", "带娃", "一家人", "家庭", "儿子", "女儿", "宝宝"],
    "elderly": ["老人", "父母", "长辈", "老年人", "爷爷奶奶", "外公外婆", "年纪大"],
    "couple": ["情侣", "夫妻", "两人", "双人", "约会", "蜜月", "伴侣"],
    "solo": ["独自", "一个人", "单人", "独行", "独自旅行", "一个人来"],
    "photographer": ["拍照", "摄影", "照片", "相机", "镜头", "拍摄", "摄影师", "摄影爱好者"],
    "experienced": ["老登山友", "熟悉", "第二次", "多次", "再来", "重来", "老驴"],
    "beginner": ["第一次", "首次", "新手", "不知道", "不了解", "第一次来"],
}


def _stable_unique(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_intent_patterns(base_dir: Path) -> Dict:
    config_path = base_dir / "config" / "intent_patterns.json"
    if not config_path.exists():
        return _DEFAULT_INTENT_PATTERNS

    try:
        loaded = _load_json(config_path)
    except Exception:
        return _DEFAULT_INTENT_PATTERNS

    if not isinstance(loaded, dict):
        return _DEFAULT_INTENT_PATTERNS

    merged = dict(_DEFAULT_INTENT_PATTERNS)
    merged.update(loaded)
    return merged


def _load_visitor_type_patterns(project_root: Path) -> Dict[str, List[str]]:
    config_path = project_root / "task5_conditional_advice" / "config" / "visitor_type_patterns.json"
    if not config_path.exists():
        return _DEFAULT_VISITOR_TYPE_PATTERNS

    try:
        loaded = _load_json(config_path)
    except Exception:
        return _DEFAULT_VISITOR_TYPE_PATTERNS

    if not isinstance(loaded, dict):
        return _DEFAULT_VISITOR_TYPE_PATTERNS

    parsed: Dict[str, List[str]] = {}
    for vtype, meta in loaded.items():
        if not isinstance(meta, dict):
            continue
        keywords = meta.get("keywords", [])
        if isinstance(keywords, list):
            parsed[vtype] = [str(k) for k in keywords if str(k).strip()]

    return parsed if parsed else _DEFAULT_VISITOR_TYPE_PATTERNS


def _detect_scenic_spot(text: str, scenic_spots: List[str]) -> Optional[str]:
    for spot in scenic_spots:
        if spot in text:
            return spot
    return None


def _detect_visitor_type(text: str, visitor_patterns: Dict[str, List[str]]) -> Optional[str]:
    # 优先匹配family/elderly/couple等具体类型，不把general作为显式输出
    ranked_types = [
        "family",
        "elderly",
        "couple",
        "solo",
        "photographer",
        "experienced",
        "beginner",
    ]

    scores = {}
    for vtype, keywords in visitor_patterns.items():
        if vtype not in ranked_types:
            continue
        hit_count = sum(1 for kw in keywords if kw and kw in text)
        if hit_count > 0:
            scores[vtype] = hit_count

    if not scores:
        return None

    return max(
        scores.items(),
        key=lambda x: (x[1], -ranked_types.index(x[0]) if x[0] in ranked_types else -999),
    )[0]


def _detect_duration(text: str, duration_patterns: Dict[str, List[str]]) -> Optional[str]:
    scores = {}
    for dtype, keywords in duration_patterns.items():
        if not isinstance(keywords, list):
            continue
        hit_count = sum(1 for kw in keywords if kw and kw in text)
        if hit_count > 0:
            scores[dtype] = hit_count

    if not scores:
        return None

    priority = ["two_hours", "half_day", "one_day", "multi_day"]
    return max(
        scores.items(),
        key=lambda x: (x[1], -priority.index(x[0]) if x[0] in priority else -999),
    )[0]


def _extract_condition_keywords(text: str, keyword_groups: Dict[str, List[str]]) -> List[str]:
    extracted = []

    for keywords in keyword_groups.values():
        if not isinstance(keywords, list):
            continue
        for kw in keywords:
            if kw and kw in text:
                extracted.append(kw)

    # 补充通用模式
    regex_patterns = [
        r"\d+小时",
        r"\d+天",
    ]
    for pattern in regex_patterns:
        for match in re.findall(pattern, text):
            extracted.append(match)

    return _stable_unique(extracted)


def parse_query(text: str, project_root: Optional[str] = None) -> ParsedQuery:
    """
    解析用户自然语言查询为结构化槽位。

    Public API:
        parse_query(text: str) -> ParsedQuery
    """
    raw_text = (text or "").strip()
    if not raw_text:
        return ParsedQuery(raw_text="")

    base_dir = Path(__file__).resolve().parent
    root_dir = Path(project_root) if project_root else base_dir.parent

    intent_patterns = _load_intent_patterns(base_dir)
    visitor_patterns = _load_visitor_type_patterns(root_dir)

    scenic_spot = _detect_scenic_spot(raw_text, intent_patterns.get("scenic_spots", []))
    visitor_type = _detect_visitor_type(raw_text, visitor_patterns)
    duration = _detect_duration(raw_text, intent_patterns.get("duration_patterns", {}))
    condition_keywords = _extract_condition_keywords(raw_text, intent_patterns.get("condition_keywords", {}))

    return ParsedQuery(
        raw_text=raw_text,
        scenic_spot=scenic_spot,
        visitor_type=visitor_type,
        duration=duration,
        condition_keywords=condition_keywords,
    )
