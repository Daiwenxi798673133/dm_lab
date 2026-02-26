#!/usr/bin/env python3

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

TASK7_DIR = Path(__file__).resolve().parents[1]
if str(TASK7_DIR) not in sys.path:
    sys.path.insert(0, str(TASK7_DIR))

import main as qa_main
from knowledge_index import ConditionSuggestion, SpotKnowledge, load_spot_knowledge
from query_parser import parse_query
from rule_engine import match_suggestions


PROJECT_ROOT = TASK7_DIR.parent


def test_parse_family_one_day_query() -> None:
    query = parse_query("我想带孩子玩一天", project_root=str(PROJECT_ROOT))
    assert query.visitor_type == "family"
    assert query.duration == "one_day"
    assert "孩子" in query.condition_keywords
    assert "一天" in query.condition_keywords


def test_interactive_prompt_spot_then_answer(monkeypatch, capsys) -> None:
    # 不传--spot，触发交互追问景区
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: "故宫")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--query",
            "我想带孩子玩一天",
            "--project-root",
            str(PROJECT_ROOT),
            "--topk",
            "3",
        ],
    )

    exit_code = qa_main.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "未识别到景区，请先选择景区" in output
    assert "景区: 故宫" in output


def test_fallback_strategy_returns_non_empty_suggestions() -> None:
    knowledge = load_spot_knowledge(str(PROJECT_ROOT), "故宫")
    query = parse_query("我想带孩子玩一天", project_root=str(PROJECT_ROOT))
    query = replace(query, scenic_spot="故宫")

    result = match_suggestions(query, knowledge, top_k=5, project_root=str(PROJECT_ROOT))

    assert result.suggestions
    assert result.fallback_tier_used in {2, 3, 4}


def test_ranking_prefers_high_confidence_and_support() -> None:
    synthetic_knowledge = SpotKnowledge(
        scenic_spot="测试景区",
        route_summary=["A点", "B点", "C点"],
        suggestions=[
            ConditionSuggestion(
                advice_text="建议走A点到B点的快速路线",
                poi="A点",
                condition_text="一天快速游",
                condition_type="route",
                condition_subtype="route",
                confidence=0.95,
                support_count=3,
            ),
            ConditionSuggestion(
                advice_text="建议随便逛逛",
                poi="X点",
                condition_text="一般情况",
                condition_type="route",
                condition_subtype="route",
                confidence=0.80,
                support_count=1,
            ),
        ],
    )

    # 不给时长/游客类型信号，触发同层级候选排序
    query = parse_query("我想去逛逛", project_root=str(PROJECT_ROOT))
    result = match_suggestions(query, synthetic_knowledge, top_k=2, project_root=str(PROJECT_ROOT))

    assert len(result.suggestions) == 2
    assert result.suggestions[0].score >= result.suggestions[1].score
    assert result.suggestions[0].poi == "A点"


def test_missing_graph_file_should_raise(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_spot_knowledge(str(tmp_path), "故宫")
