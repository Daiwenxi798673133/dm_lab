#!/usr/bin/env python3
"""
路线解析器 - 解析不同格式的官方游览路线
支持三种格式：
1. 九寨沟格式：箭头连接 + 时间范围
2. 故宫格式：编号列表
3. 黄山格式：多线路选择
"""

import re
import json
from typing import Dict, List, Any, Optional


def get_time_period(time_str: str) -> str:
    """将时间字符串映射到时段（上午/中午/下午/晚上）"""
    # 提取小时数
    hour_match = re.search(r'(\d{1,2}):', time_str)
    if hour_match:
        hour = int(hour_match.group(1))
        if 5 <= hour < 9:
            return "清晨"
        elif 9 <= hour < 11:
            return "上午"
        elif 11 <= hour < 13:
            return "中午"
        elif 13 <= hour < 17:
            return "下午"
        elif 17 <= hour < 19:
            return "傍晚"
        else:
            return "晚上"
    return "未知时段"


def parse_jiuzhaigou_route(text: str) -> Dict[str, Any]:
    """解析九寨沟格式：景点A→景点B（时间范围 时长 交通）"""
    routes = []

    # 匹配路线节点模式：起点→终点(时间范围 详细信息)
    # 支持两种模式：
    # 1. A→B(时间 信息)
    # 2. A→B→C(时间 信息)

    # 先找到所有带时间的路线段
    segments = re.findall(r'([^→\n]+?)→([^→\n]+?)\((\d{1,2}:\d{2})[-~](\d{1,2}:\d{2})[^)]*\)', text)

    for start_poi, end_poi, time_start, time_end in segments:
        start_poi = start_poi.strip()
        end_poi = end_poi.strip()

        # 提取该段的详细信息
        full_match = re.search(
            re.escape(start_poi) + r'→' + re.escape(end_poi) + r'\(([^)]+)\)',
            text
        )

        details = full_match.group(1) if full_match else ""

        # 提取交通方式
        transport = "步行"
        if "观光车" in details:
            transport = "观光车"
        elif "乘车" in details:
            transport = "乘车"
        elif "缆车" in details or "索道" in details:
            transport = "索道/缆车"
        elif "步行" in details:
            transport = "步行"

        # 提取时长
        duration = ""
        duration_match = re.search(r'(\d+[分钟小时]+|约?\d+[分钟小时]+|半个?小时)', details)
        if duration_match:
            duration = duration_match.group(1)

        # 计算时段
        period = get_time_period(time_start)

        routes.append({
            "from_poi": start_poi,
            "to_poi": end_poi,
            "poi": end_poi,  # 主要节点
            "time_start": time_start,
            "time_end": time_end,
            "period": period,
            "transport": transport,
            "duration": duration,
            "details": details
        })

    # 提取所有景点（从routes中）
    all_pois_set = set()

    # 添加起点
    if routes:
        all_pois_set.add(routes[0].get('from_poi', ''))

    # 添加所有终点
    for route in routes:
        all_pois_set.add(route.get('to_poi', ''))
        all_pois_set.add(route.get('poi', ''))

    # 过滤空值并排序
    all_pois = sorted([p for p in all_pois_set if p and len(p) >= 2])

    return {
        "scenic_spot": "九寨沟",
        "route_format": "structured_time_route",
        "total_pois": len(all_pois),
        "pois": all_pois,
        "routes": routes
    }


def parse_gugong_route(text: str) -> Dict[str, Any]:
    """解析故宫格式：编号列表"""
    routes = []

    # 匹配编号列表：数字. 景点名称
    numbered_items = re.findall(r'(\d+)\.\s*([^\n]+)', text)

    for num, poi in numbered_items:
        poi = poi.strip()

        # 提取括号内的信息（如：钟表馆、珍宝馆）
        alias_match = re.search(r'[（(]([^）)]+)[）)]', poi)
        alias = alias_match.group(1) if alias_match else None

        # 清理景点名称
        clean_poi = re.sub(r'[（(][^）)]+[）)]', '', poi).strip()

        routes.append({
            "sequence": int(num),
            "poi": clean_poi,
            "alias": alias,
            "full_text": poi
        })

    # 提取所有POI名称
    all_pois = [r["poi"] for r in routes]
    if routes:
        all_pois.insert(0, "午门")  # 起始点

    return {
        "scenic_spot": "故宫",
        "route_format": "numbered_list",
        "total_pois": len(routes),
        "pois": all_pois,
        "routes": routes
    }


def parse_huangshan_route(text: str) -> Dict[str, Any]:
    """解析黄山格式：多线路选择"""
    routes = []

    # 匹配线路：线路X:...
    route_sections = re.split(r'线路[一二三四五六七八九十]+[：:]', text)

    # 提取线路编号
    route_numbers = re.findall(r'线路([一二三四五六七八九十]+)[：:]', text)

    for i, (route_num, section) in enumerate(zip(route_numbers, route_sections[1:]), start=1):  # 跳过第一个空部分
        if not section.strip():
            continue

        # 解析线路中的节点（用→或→连接）
        nodes = re.split(r'→|→', section.strip())

        # 清理节点名称
        clean_nodes = []
        for node in nodes:
            node = node.strip()
            # 移除括号内的详细信息
            node = re.sub(r'[（(][^）)]+[）)]', '', node)
            node = node.strip()
            if node and len(node) >= 2:
                clean_nodes.append(node)

        # 提取路线特征
        route_features = {
            "route_id": f"route_{i}",
            "route_name": f"线路{route_num}",
            "nodes": clean_nodes,
            "total_nodes": len(clean_nodes)
        }

        # 检测路线类型
        if "北大门" in section:
            route_features["entrance"] = "北大门"
        elif "南大门" in section:
            route_features["entrance"] = "南大门"

        if "云谷索道" in section:
            route_features["cableway"] = "云谷索道"
        elif "玉屏索道" in section:
            route_features["cableway"] = "玉屏索道"
        elif "太平索道" in section:
            route_features["cableway"] = "太平索道"

        routes.append(route_features)

    # 收集所有出现的景点
    all_pois = []
    for route in routes:
        all_pois.extend(route["nodes"])

    # 去重并统计频率
    from collections import Counter
    poi_freq = Counter(all_pois)

    return {
        "scenic_spot": "黄山",
        "route_format": "multi_route_selection",
        "total_routes": len(routes),
        "total_pois": len(poi_freq),
        "pois": list(poi_freq.keys()),
        "poi_frequency": dict(poi_freq),
        "routes": routes
    }


class RouteParser:
    """路线解析器 - 统一接口"""

    @staticmethod
    def parse(scenic_spot: str, route_text: str) -> Dict[str, Any]:
        """根据景区类型解析路线"""
        if scenic_spot == "九寨沟":
            return parse_jiuzhaigou_route(route_text)
        elif scenic_spot == "故宫":
            return parse_gugong_route(route_text)
        elif scenic_spot == "黄山":
            return parse_huangshan_route(route_text)
        else:
            return {
                "scenic_spot": scenic_spot,
                "route_format": "unknown",
                "error": "Unsupported scenic spot"
            }


class TimeHierarchyBuilder:
    """时间层级结构构建器"""

    @staticmethod
    def build_hierarchy(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建时间维度的游览层级结构"""
        scenic_spot = parsed_data.get("scenic_spot", "")
        route_format = parsed_data.get("route_format", "")

        if scenic_spot == "九寨沟" and route_format == "structured_time_route":
            return TimeHierarchyBuilder._build_jiuzhaigou_hierarchy(parsed_data)
        elif scenic_spot == "故宫" and route_format == "numbered_list":
            return TimeHierarchyBuilder._build_gugong_hierarchy(parsed_data)
        elif scenic_spot == "黄山" and route_format == "multi_route_selection":
            return TimeHierarchyBuilder._build_huangshan_hierarchy(parsed_data)
        else:
            return {"error": "Unsupported format"}

    @staticmethod
    def _build_jiuzhaigou_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """构建九寨沟的时间层级结构"""
        hierarchy = {
            "scenic_spot": "九寨沟",
            "structure_type": "time_based",
            "hierarchy": {}
        }

        # 按时段分组
        periods = {}
        for route in data.get("routes", []):
            period = route.get("period", "未知时段")
            if period not in periods:
                periods[period] = []

            periods[period].append({
                "poi": route.get("poi", ""),
                "time_start": route.get("time_start", ""),
                "time_end": route.get("time_end", ""),
                "transport": route.get("transport", ""),
                "duration": route.get("duration", ""),
                "details": route.get("details", "")
            })

        # 构建层级结构
        period_order = ["清晨", "上午", "中午", "下午", "傍晚", "晚上"]
        for period in period_order:
            if period in periods:
                hierarchy["hierarchy"][period] = {
                    "time_range": TimeHierarchyBuilder._get_period_range(period),
                    "activities": periods[period],
                    "activity_count": len(periods[period])
                }

        return hierarchy

    @staticmethod
    def _build_gugong_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """构建故宫的层级结构（基于编号顺序）"""
        hierarchy = {
            "scenic_spot": "故宫",
            "structure_type": "sequence_based",
            "hierarchy": {
                "游览路线": {
                    "sections": []
                }
            }
        }

        # 将路线分组（前、中、后）
        routes = data.get("routes", [])
        total = len(routes)

        # 分为三个部分
        if total > 0:
            third = total // 3
            hierarchy["hierarchy"]["游览路线"]["sections"] = [
                {
                    "name": "前部（外朝）",
                    "pois": [r["poi"] for r in routes[:third + 1]]
                },
                {
                    "name": "中部（内廷）",
                    "pois": [r["poi"] for r in routes[third + 1:2 * third + 1]]
                },
                {
                    "name": "后部（御花园等）",
                    "pois": [r["poi"] for r in routes[2 * third + 1:]]
                }
            ]

        hierarchy["hierarchy"]["游览路线"]["total_pois"] = total
        hierarchy["hierarchy"]["游览路线"]["full_sequence"] = [r["poi"] for r in routes]

        return hierarchy

    @staticmethod
    def _build_huangshan_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """构建黄山的层级结构（基于线路选择）"""
        hierarchy = {
            "scenic_spot": "黄山",
            "structure_type": "route_selection_based",
            "hierarchy": {
                "可选线路": {}
            }
        }

        for route in data.get("routes", []):
            route_name = route.get("route_name", "")
            hierarchy["hierarchy"]["可选线路"][route_name] = {
                "entrance": route.get("entrance", ""),
                "cableway": route.get("cableway", ""),
                "nodes": route.get("nodes", []),
                "total_nodes": route.get("total_nodes", 0)
            }

        # 统计所有景点的出现频率
        poi_freq = data.get("poi_frequency", {})
        hierarchy["common_pois"] = {
            "high_frequency": [poi for poi, freq in poi_freq.items() if freq >= 3],
            "medium_frequency": [poi for poi, freq in poi_freq.items() if freq == 2],
            "low_frequency": [poi for poi, freq in poi_freq.items() if freq == 1]
        }

        return hierarchy

    @staticmethod
    def _get_period_range(period: str) -> str:
        """获取时段的时间范围"""
        ranges = {
            "清晨": "5:00-9:00",
            "上午": "9:00-11:00",
            "中午": "11:00-13:00",
            "下午": "13:00-17:00",
            "傍晚": "17:00-19:00",
            "晚上": "19:00-23:00"
        }
        return ranges.get(period, "")


def main():
    """测试函数"""
    import pandas as pd

    print("=" * 60)
    print("路线解析测试")
    print("=" * 60)

    # 读取数据
    df = pd.read_excel('data_cleaned.xlsx')

    for idx, row in df.iterrows():
        scenic_spot = row['景区名称']
        route_text = row['官方游览路线']

        if pd.isna(route_text):
            continue

        print(f"\n{'='*60}")
        print(f"解析 {scenic_spot} 官方路线")
        print(f"{'='*60}")

        # 解析路线
        parsed = RouteParser.parse(scenic_spot, route_text)

        # 构建层级结构
        hierarchy = TimeHierarchyBuilder.build_hierarchy(parsed)

        print(f"\n路线格式: {parsed.get('route_format', 'unknown')}")
        print(f"景点数量: {parsed.get('total_pois', 0)}")
        print(f"\n前10个景点: {parsed.get('pois', [])[:10]}")

        print(f"\n层级结构类型: {hierarchy.get('structure_type', 'unknown')}")

        # 保存结果
        with open(f'route_hierarchy/{scenic_spot}_hierarchy.json', 'w', encoding='utf-8') as f:
            json.dump({
                "parsed": parsed,
                "hierarchy": hierarchy
            }, f, ensure_ascii=False, indent=2)

        print(f"\n已保存: route_hierarchy/{scenic_spot}_hierarchy.json")


if __name__ == '__main__':
    # 创建输出目录
    import os
    if not os.path.exists('route_hierarchy'):
        os.makedirs('route_hierarchy')

    main()
