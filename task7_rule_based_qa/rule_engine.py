#!/usr/bin/env python3
"""
任务7：规则驱动问答 - 规则引擎

功能：
1. 候选建议分层回退匹配
2. 统一打分与去重
3. 输出可解释结果
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from knowledge_index import ConditionSuggestion, SpotKnowledge
from query_parser import ParsedQuery


@dataclass
class SuggestionItem:
    advice_text: str
    poi: str
    condition_text: str
    condition_type: str
    score: float
    matched_rules: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QAResult:
    parsed_query: ParsedQuery
    scenic_spot: str
    suggestions: List[SuggestionItem]
    route_summary: List[str]
    fallback_tier_used: int


_DEFAULT_RULE_WEIGHTS = {
    "tier_base": {
        "tier1": 80.0,
        "tier2": 60.0,
        "tier3": 45.0,
        "tier4": 30.0,
    },
    "keyword_overlap": 6.0,
    "confidence_bonus": 18.0,
    "support_count_bonus": 3.0,
    "recommended_route_bonus": 5.0,
}

_VISITOR_KEYWORDS = {
    "family": ["孩子", "小孩", "儿童", "亲子", "带娃", "家庭", "一家人", "宝宝"],
    "elderly": ["老人", "长辈", "老年", "父母", "爷爷奶奶"],
    "couple": ["情侣", "夫妻", "约会", "蜜月", "伴侣"],
    "solo": ["独自", "一个人", "独行", "单人"],
    "photographer": ["拍照", "摄影", "照片", "相机"],
    "experienced": ["熟悉", "第二次", "多次", "老驴", "经验"],
    "beginner": ["第一次", "首次", "新手", "不了解"],
}

_DURATION_KEYWORDS = {
    "two_hours": ["2小时", "两小时", "快速游", "短线"],
    "half_day": ["半天", "半日"],
    "one_day": ["一天", "一日", "全天", "整天"],
    "multi_day": ["两天", "2天", "三天", "3天", "多日", "几天"],
}



def _load_rule_weights(project_root: Optional[str] = None) -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    config_path = base_dir / "config" / "rule_weights.json"
    if not config_path.exists():
        return _DEFAULT_RULE_WEIGHTS

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        return _DEFAULT_RULE_WEIGHTS

    if not isinstance(loaded, dict):
        return _DEFAULT_RULE_WEIGHTS

    merged = dict(_DEFAULT_RULE_WEIGHTS)
    merged.update(loaded)

    tier_base = dict(_DEFAULT_RULE_WEIGHTS["tier_base"])
    tier_base.update(loaded.get("tier_base", {}))
    merged["tier_base"] = tier_base
    return merged


def _normalize_text(text: str) -> str:
    return "".join((text or "").strip().split())


def _infer_visitor_tags(text: str) -> Set[str]:
    tags = set()
    for visitor_type, keywords in _VISITOR_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.add(visitor_type)
    return tags


def _infer_duration_tags(text: str) -> Set[str]:
    tags = set()
    for duration_type, keywords in _DURATION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.add(duration_type)
    return tags


def _keyword_overlap(query_keywords: List[str], candidate_text: str) -> int:
    if not query_keywords:
        return 0
    return sum(1 for kw in set(query_keywords) if kw and kw in candidate_text)


def _build_candidate_text(candidate: ConditionSuggestion) -> str:
    return " ".join(
        [
            candidate.condition_text,
            candidate.advice_text,
            candidate.poi,
            candidate.condition_type,
            candidate.condition_subtype,
        ]
    )


def _tier3_high_conf(candidate: ConditionSuggestion) -> bool:
    return (
        candidate.condition_type in {"route", "time", "ticketing", "time_duration", "transport"}
        and candidate.confidence >= 0.75
    )


def _score_candidate(
    tier: int,
    overlap_count: int,
    candidate: ConditionSuggestion,
    is_recommended_poi: bool,
    weights: Dict[str, Any],
) -> float:
    tier_key = f"tier{tier}"
    tier_base = float(weights.get("tier_base", {}).get(tier_key, 0.0))
    score = tier_base
    score += overlap_count * float(weights.get("keyword_overlap", 0.0))
    score += float(candidate.confidence) * float(weights.get("confidence_bonus", 0.0))
    score += min(int(candidate.support_count), 3) * float(weights.get("support_count_bonus", 0.0))
    if is_recommended_poi:
        score += float(weights.get("recommended_route_bonus", 0.0))
    return round(score, 3)


def _deduplicate(items: List[SuggestionItem]) -> List[SuggestionItem]:
    best_by_advice: Dict[str, SuggestionItem] = {}
    for item in items:
        key = _normalize_text(item.advice_text)
        if not key:
            key = f"EMPTY_ADVICE::{_normalize_text(item.condition_text)}::{_normalize_text(item.poi)}"
        existing = best_by_advice.get(key)
        if existing is None or item.score > existing.score:
            best_by_advice[key] = item

    best_by_condition_poi: Dict[str, SuggestionItem] = {}
    for item in best_by_advice.values():
        key = f"{_normalize_text(item.condition_text)}::{_normalize_text(item.poi)}"
        existing = best_by_condition_poi.get(key)
        if existing is None or item.score > existing.score:
            best_by_condition_poi[key] = item

    return list(best_by_condition_poi.values())


def _build_weak_fallback(knowledge: SpotKnowledge, query: ParsedQuery) -> List[SuggestionItem]:
    route = knowledge.route_summary
    if route:
        route_text = " -> ".join(route[:12])
        return [
            SuggestionItem(
                advice_text=f"暂无高置信匹配，建议先按推荐路线游览：{route_text}",
                poi=route[0],
                condition_text="推荐路线兜底",
                condition_type="route",
                score=25.0,
                matched_rules=["tier_4", "weak_fallback_route"],
                evidence={"reason": "no_conditional_candidates"},
            )
        ]

    return [
        SuggestionItem(
            advice_text="暂无高置信匹配，建议优先查看景区官方路线与门票信息。",
            poi="",
            condition_text="通用兜底",
            condition_type="other",
            score=20.0,
            matched_rules=["tier_4", "weak_fallback_generic"],
            evidence={"reason": "no_route_summary"},
        )
    ]


def match_suggestions(
    query: ParsedQuery,
    knowledge: SpotKnowledge,
    top_k: int = 5,
    project_root: Optional[str] = None,
) -> QAResult:
    """
    Public API:
        match_suggestions(query: ParsedQuery, knowledge: SpotKnowledge, top_k: int = 5) -> QAResult
    """
    weights = _load_rule_weights(project_root)
    candidates = knowledge.suggestions or []

    recommended_pois = set(knowledge.route_summary)
    selected_items: List[SuggestionItem] = []
    used_tier = 4

    for tier in [1, 2, 3, 4]:
        tier_items: List[SuggestionItem] = []
        for candidate in candidates:
            candidate_text = _build_candidate_text(candidate)
            visitor_tags = _infer_visitor_tags(candidate_text)
            duration_tags = _infer_duration_tags(candidate_text)
            overlap_count = _keyword_overlap(query.condition_keywords, candidate_text)

            visitor_match = bool(query.visitor_type and query.visitor_type in visitor_tags)
            duration_match = bool(query.duration and query.duration in duration_tags)

            qualifies = False
            if tier == 1:
                qualifies = visitor_match and duration_match
            elif tier == 2:
                slot_match = visitor_match or duration_match
                qualifies = slot_match and (overlap_count > 0 or not query.condition_keywords)
            elif tier == 3:
                qualifies = _tier3_high_conf(candidate)
            elif tier == 4:
                qualifies = True

            if not qualifies:
                continue

            is_recommended_poi = candidate.poi in recommended_pois if candidate.poi else False
            score = _score_candidate(tier, overlap_count, candidate, is_recommended_poi, weights)

            matched_rules = [f"tier_{tier}"]
            if visitor_match:
                matched_rules.append("visitor_type_match")
            if duration_match:
                matched_rules.append("duration_match")
            if overlap_count > 0:
                matched_rules.append(f"keyword_overlap={overlap_count}")
            if _tier3_high_conf(candidate):
                matched_rules.append("high_conf_condition")
            if is_recommended_poi:
                matched_rules.append("recommended_route_poi")

            tier_items.append(
                SuggestionItem(
                    advice_text=candidate.advice_text,
                    poi=candidate.poi,
                    condition_text=candidate.condition_text,
                    condition_type=candidate.condition_type,
                    score=score,
                    matched_rules=matched_rules,
                    evidence={
                        "confidence": candidate.confidence,
                        "support_count": candidate.support_count,
                        "condition_subtype": candidate.condition_subtype,
                        "raw": candidate.evidence,
                    },
                )
            )

        tier_items = _deduplicate(tier_items)
        tier_items.sort(key=lambda x: x.score, reverse=True)

        if tier_items:
            selected_items = tier_items
            used_tier = tier
            break

    if not selected_items:
        selected_items = _build_weak_fallback(knowledge, query)
        used_tier = 4

    if top_k <= 0:
        top_k = 5

    return QAResult(
        parsed_query=query,
        scenic_spot=knowledge.scenic_spot,
        suggestions=selected_items[:top_k],
        route_summary=knowledge.route_summary,
        fallback_tier_used=used_tier,
    )
