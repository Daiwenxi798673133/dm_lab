#!/usr/bin/env python3
"""
任务7：程序性知识应用 - 规则驱动终端问答

示例：
    python3 main.py
    python3 main.py --query "我想带孩子玩一天" --spot 故宫 --topk 5
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import List

from knowledge_index import list_available_spots, load_spot_knowledge
from query_parser import ParsedQuery, parse_query
from rule_engine import QAResult, match_suggestions


VISITOR_TYPE_LABELS = {
    "family": "亲子游",
    "elderly": "老年游",
    "couple": "情侣游",
    "solo": "独自游",
    "photographer": "摄影游",
    "experienced": "经验丰富",
    "beginner": "新手",
}

DURATION_LABELS = {
    "two_hours": "2小时",
    "half_day": "半天",
    "one_day": "一天",
    "multi_day": "多日",
}


def _prompt_spot(available_spots: List[str]) -> str:
    print("未识别到景区，请先选择景区：")
    for idx, spot in enumerate(available_spots, 1):
        print(f"  {idx}. {spot}")

    while True:
        raw = input("请输入景区名称或编号: ").strip()
        if not raw:
            continue

        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(available_spots):
                return available_spots[index - 1]

        if raw in available_spots:
            return raw

        print("输入无效，请重新输入。")


def _format_parsed_query(parsed: ParsedQuery) -> None:
    visitor_type = parsed.visitor_type or "未识别"
    if parsed.visitor_type:
        visitor_type = f"{parsed.visitor_type} ({VISITOR_TYPE_LABELS.get(parsed.visitor_type, '未定义标签')})"

    duration = parsed.duration or "未识别"
    if parsed.duration:
        duration = f"{parsed.duration} ({DURATION_LABELS.get(parsed.duration, '未定义标签')})"

    keywords = "、".join(parsed.condition_keywords) if parsed.condition_keywords else "无"

    print("\n[解析槽位]")
    print(f"  景区: {parsed.scenic_spot or '未识别'}")
    print(f"  游客类型: {visitor_type}")
    print(f"  时长: {duration}")
    print(f"  条件关键词: {keywords}")


def _print_result(result: QAResult) -> None:
    print("\n[匹配结果]")
    print(f"  使用回退层级: Tier-{result.fallback_tier_used}")
    print(f"  景区: {result.scenic_spot}")

    if not result.suggestions:
        print("  暂无建议。")
    else:
        for idx, item in enumerate(result.suggestions, 1):
            rules = ", ".join(item.matched_rules) if item.matched_rules else "-"
            confidence = item.evidence.get("confidence", "-")
            support_count = item.evidence.get("support_count", "-")

            print(f"\n  {idx}. 建议: {item.advice_text}")
            print(f"     分数: {item.score}")
            print(f"     POI: {item.poi or '-'}")
            print(f"     条件: {item.condition_text or '-'} ({item.condition_type})")
            print(f"     命中规则: {rules}")
            print(f"     证据: confidence={confidence}, support_count={support_count}")

    if result.route_summary:
        print("\n[推荐路线摘要]")
        print("  " + " -> ".join(result.route_summary[:15]))


def main() -> int:
    parser = argparse.ArgumentParser(description="任务7：规则驱动终端问答")
    parser.add_argument("--query", type=str, help="用户问题，例如：我想带孩子玩一天")
    parser.add_argument("--spot", type=str, help="景区名称：九寨沟/故宫/黄山")
    parser.add_argument("--topk", type=int, default=5, help="返回建议条数（默认5）")
    parser.add_argument("--project-root", type=str, help="项目根目录（默认自动推断）")

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    project_root = Path(args.project_root) if args.project_root else base_dir.parent

    available_spots = list_available_spots(str(project_root))
    if not available_spots:
        print("错误：未找到 task6 图谱输出，请先运行 task6。")
        return 1

    query_text = args.query.strip() if args.query else ""
    if not query_text:
        query_text = input("请输入旅游需求（如：我想带孩子玩一天）: ").strip()

    if not query_text:
        print("错误：输入为空。")
        return 1

    parsed_query = parse_query(query_text, project_root=str(project_root))

    spot = args.spot or parsed_query.scenic_spot
    if not spot:
        spot = _prompt_spot(available_spots)

    if spot not in available_spots:
        print(f"错误：景区 '{spot}' 不在可用列表: {', '.join(available_spots)}")
        return 1

    parsed_query = replace(parsed_query, scenic_spot=spot)

    try:
        knowledge = load_spot_knowledge(str(project_root), spot)
    except FileNotFoundError as e:
        print(f"错误：{e}")
        return 1

    result = match_suggestions(
        parsed_query,
        knowledge,
        top_k=args.topk,
        project_root=str(project_root),
    )

    print("=" * 62)
    print("任务7：规则驱动终端问答")
    print("=" * 62)
    print(f"\n输入: {query_text}")

    _format_parsed_query(parsed_query)
    _print_result(result)

    print("\n" + "=" * 62)
    print("完成")
    print("=" * 62)

    return 0


if __name__ == "__main__":
    sys.exit(main())
