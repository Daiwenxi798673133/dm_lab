# 任务7：规则驱动的终端问答建议系统

## 任务目标
1. 基于 task6 知识图谱构建简单问答规则。
2. 用户输入如“我想带孩子玩一天”，系统在终端返回可解释建议。
3. 不使用大模型，仅使用规则匹配和分层回退。

## 文件结构

```text
task7_rule_based_qa/
├── README.md
├── main.py
├── query_parser.py
├── knowledge_index.py
├── rule_engine.py
├── config/
│   ├── intent_patterns.json
│   └── rule_weights.json
└── tests/
    └── test_task7_rule_engine.py
```

## 数据依赖

1. `task6_knowledge_fusion/output/knowledge_graph/*_graph.json`
2. `task6_knowledge_fusion/output/knowledge_graph/*_quality_report.json`
3. `task5_conditional_advice/config/visitor_type_patterns.json`

## 运行方式

### 1) 交互模式

```bash
cd task7_rule_based_qa
python3 main.py
```

- 输入需求后，若未识别景区，会先追问景区（九寨沟/故宫/黄山）。

### 2) 非交互模式

```bash
cd task7_rule_based_qa
python3 main.py --query "我想带孩子玩一天" --spot 故宫 --topk 5
```

## 核心规则

### 查询槽位
- `scenic_spot`
- `visitor_type`
- `duration`
- `condition_keywords`

### 候选来源
- 图谱 `conditional` 边 + `condition` 节点
- 推荐路线 `sequence` 边（`is_recommended=true`）

### 分层回退
1. Tier-1：游客类型 + 时长双命中
2. Tier-2：游客类型或时长单命中 + 条件关键词重叠
3. Tier-3：`route/time/ticketing/time_duration/transport` 等高置信建议
4. Tier-4：全量候选 + 推荐路线兜底

### 打分

```text
score = tier_base
      + keyword_overlap * keyword_overlap_weight
      + confidence * confidence_bonus
      + min(support_count, 3) * support_count_bonus
      + recommended_route_bonus(if poi in route)
```

## 输出说明

终端输出包含：
1. 槽位解析结果
2. 使用的回退层级
3. Top-K 建议（分数、命中规则、证据）
4. 推荐路线摘要

## 测试

```bash
python3 -m pytest task7_rule_based_qa/tests/test_task7_rule_engine.py
```

测试覆盖：
1. 查询解析
2. 分层回退
3. 排序逻辑
4. 缺失图谱文件异常
