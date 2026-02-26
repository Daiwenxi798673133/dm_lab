#!/usr/bin/env python3
"""
任务7：规则驱动问答 - 知识索引模块

功能：
1. 加载 task6 图谱与质量报告
2. 抽取条件建议候选
3. 抽取推荐路线摘要
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ConditionSuggestion:
    advice_text: str
    poi: str
    condition_text: str
    condition_type: str
    condition_subtype: str
    confidence: float
    support_count: int
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpotKnowledge:
    scenic_spot: str
    suggestions: List[ConditionSuggestion]
    route_summary: List[str]
    recommended_route_id: str = ""
    recommended_route_reason: str = ""
    quality_report: Dict[str, Any] = field(default_factory=dict)


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _knowledge_graph_dir(project_root: str) -> Path:
    return Path(project_root) / "task6_knowledge_fusion" / "output" / "knowledge_graph"


def list_available_spots(project_root: str) -> List[str]:
    """Public API: 获取可用景区列表。"""
    base_dir = _knowledge_graph_dir(project_root)
    if not base_dir.exists():
        return []

    spots = []
    for graph_path in sorted(base_dir.glob("*_graph.json")):
        spots.append(graph_path.name.replace("_graph.json", ""))

    return spots


def _build_node_lookup(graph_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup = {}
    for node in graph_data.get("nodes", []):
        node_id = node.get("id", "")
        if node_id:
            lookup[node_id] = node
    return lookup


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _extract_conditional_suggestions(
    graph_data: Dict[str, Any],
    quality_report: Optional[Dict[str, Any]] = None,
) -> List[ConditionSuggestion]:
    nodes = _build_node_lookup(graph_data)
    suggestions: List[ConditionSuggestion] = []

    for edge in graph_data.get("edges", []):
        if edge.get("type") != "conditional":
            continue

        source = edge.get("source", "")
        target = edge.get("target", "")
        source_node = nodes.get(source, {})
        target_node = nodes.get(target, {})

        source_type = source_node.get("type")
        target_type = target_node.get("type")

        if source_type != "condition" or target_type != "poi":
            continue

        cond_props = source_node.get("properties", {})
        edge_props = edge.get("properties", {})

        advice_text = edge_props.get("advice", "")
        if not advice_text:
            advice_samples = edge_props.get("advice_samples", [])
            if isinstance(advice_samples, list) and advice_samples:
                advice_text = str(advice_samples[0])

        if not advice_text:
            node_advice_samples = cond_props.get("advice_samples", [])
            if isinstance(node_advice_samples, list) and node_advice_samples:
                advice_text = str(node_advice_samples[0])

        condition_text = (
            cond_props.get("raw_condition")
            or cond_props.get("display_label")
            or source_node.get("label", "")
        )

        suggestion = ConditionSuggestion(
            advice_text=str(advice_text),
            poi=str(target_node.get("label", "")),
            condition_text=str(condition_text),
            condition_type=str(cond_props.get("condition_type", "other")),
            condition_subtype=str(cond_props.get("condition_subtype", "unknown")),
            confidence=_safe_float(cond_props.get("confidence", 0.6), 0.6),
            support_count=_safe_int(edge_props.get("support_count", 1), 1),
            evidence={
                "condition_node_id": source,
                "poi_node_id": target,
                "edge_weight": _safe_float(edge_props.get("weight", 0.0), 0.0),
                "advice_samples": edge_props.get("advice_samples", []),
            },
        )
        suggestions.append(suggestion)

    if suggestions:
        return suggestions

    # 图中没有conditional边时，使用quality_report中的条件建议样本兜底
    if not quality_report:
        return []

    fallback = []
    for sample in quality_report.get("condition_advice_samples", []):
        advice_text = str(sample.get("advice", "")).strip()
        if not advice_text:
            continue
        fallback.append(
            ConditionSuggestion(
                advice_text=advice_text,
                poi=str(sample.get("poi", "")),
                condition_text=str(sample.get("condition", "")),
                condition_type=str(sample.get("condition_type", "other")),
                condition_subtype=str(sample.get("condition_subtype", "unknown")),
                confidence=0.65,
                support_count=1,
                evidence={"source": "quality_report.condition_advice_samples"},
            )
        )

    return fallback


def _extract_route_summary(graph_data: Dict[str, Any]) -> List[str]:
    nodes = _build_node_lookup(graph_data)

    sequence_edges = []
    for edge in graph_data.get("edges", []):
        if edge.get("type") != "sequence":
            continue
        props = edge.get("properties", {})
        if not props.get("is_recommended", False):
            continue

        seq_indices = props.get("recommended_sequence_indices") or props.get("sequence_indices") or []
        min_index = 10**9
        if isinstance(seq_indices, list) and seq_indices:
            try:
                min_index = min(int(v) for v in seq_indices)
            except Exception:
                min_index = 10**9

        source_label = nodes.get(edge.get("source", ""), {}).get("label", "")
        target_label = nodes.get(edge.get("target", ""), {}).get("label", "")

        if source_label and target_label:
            sequence_edges.append((min_index, source_label, target_label))

    if not sequence_edges:
        # 回退：如果没有标记推荐路线，则用全部sequence边
        for edge in graph_data.get("edges", []):
            if edge.get("type") != "sequence":
                continue
            props = edge.get("properties", {})
            seq_indices = props.get("sequence_indices") or []
            min_index = 10**9
            if isinstance(seq_indices, list) and seq_indices:
                try:
                    min_index = min(int(v) for v in seq_indices)
                except Exception:
                    min_index = 10**9
            source_label = nodes.get(edge.get("source", ""), {}).get("label", "")
            target_label = nodes.get(edge.get("target", ""), {}).get("label", "")
            if source_label and target_label:
                sequence_edges.append((min_index, source_label, target_label))

    sequence_edges.sort(key=lambda x: (x[0], x[1], x[2]))

    route = []
    for _, src, dst in sequence_edges:
        if not route:
            route.extend([src, dst])
            continue

        if route[-1] == src:
            route.append(dst)
            continue

        if src not in route:
            route.append(src)
        if dst not in route or route[-1] != dst:
            route.append(dst)

    # 保序去重
    deduped = []
    seen = set()
    for poi in route:
        if poi not in seen:
            seen.add(poi)
            deduped.append(poi)

    return deduped


def load_spot_knowledge(project_root: str, spot: str) -> SpotKnowledge:
    """Public API: 加载单个景区知识索引。"""
    base_dir = _knowledge_graph_dir(project_root)
    graph_path = base_dir / f"{spot}_graph.json"
    quality_path = base_dir / f"{spot}_quality_report.json"

    if not graph_path.exists():
        raise FileNotFoundError(f"缺少图谱文件: {graph_path}")

    graph_data = _load_json(graph_path)
    quality_report = _load_json(quality_path) if quality_path.exists() else {}

    suggestions = _extract_conditional_suggestions(graph_data, quality_report)
    route_summary = _extract_route_summary(graph_data)

    recommended = quality_report.get("recommended_route", {}) if isinstance(quality_report, dict) else {}

    return SpotKnowledge(
        scenic_spot=spot,
        suggestions=suggestions,
        route_summary=route_summary,
        recommended_route_id=str(recommended.get("route_id", "")),
        recommended_route_reason=str(recommended.get("reason", "")),
        quality_report=quality_report,
    )
