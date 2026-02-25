# 任务5：条件性游览建议的抽取

## 任务目标

1. 从游记文本中提取条件性建议（如“如果...建议...”“若是...可以...”）
2. 构建“条件 -> 建议”映射表
3. 分析不同游客类型（亲子、老人、情侣等）的建议差异

## 当前实现（已更新）

### 抽取策略

当前版本采用“规则匹配 + 回退抽取 + 多重过滤 + 去重”流程：

1. **规则匹配（命名组）**
   - `if_then`
   - `if_not_then`
   - `condition_suffix_then`
   - `for_group_then`
   - `desire_then`
2. **候选片段增强**
   - 句子切分后，生成原句/分句/相邻分句组合
3. **回退抽取**
   - 当主规则未命中时，基于建议触发词（建议/推荐/最好/可以...）回退提取
4. **质量控制**
   - 过滤叙述性误提取（如“可以看到...”）
   - 过滤明显噪声（过短、格式异常、重复片段）
5. **去重合并**
   - 同句同建议合并
   - 条件一致且建议前后缀重复的条目合并

关键代码：
- `processor.py`
- `config/condition_patterns.json`
- `config/condition_classification.json`

### 条件类型（细化后）

- `time`（时间条件）
- `weather`（天气条件）
- `crowd`（人流条件）
- `physical`（体力条件）
- `visitor_type`（游客类型）
- `budget`（预算条件）
- `time_duration`（时长条件）
- `ticketing`（票务条件）
- `transport`（交通条件）
- `route`（路线条件）
- `equipment`（装备条件）
- `policy`（规则条件）
- `other`（其他条件）

## 文件结构

```text
task5_conditional_advice/
├── README.md
├── main.py
├── processor.py
├── analyzer.py
├── visualizer.py
├── evaluator.py
├── config/
│   ├── condition_patterns.json
│   ├── condition_classification.json
│   └── visitor_type_patterns.json
└── output/
    ├── conditional_advice.json
    ├── condition_mapping.json
    ├── visitor_analysis.json
    ├── statistics_report.json
    ├── annotation_template.xlsx
    └── visualizations/
        ├── condition_distribution.png
        ├── visitor_comparison.png
        ├── advice_network.png
        └── scenic_spot_comparison.png
```

## 使用方法

### 1. 完整流程

```bash
cd task5_conditional_advice
python3 main.py
```

### 2. 分阶段运行

```bash
python3 main.py --extract
python3 main.py --analyze
python3 main.py --visualize
python3 main.py --evaluate
```

## 输出说明

### `output/conditional_advice.json`

每条抽取记录包含：
- `condition.text/type/normalized`
- `advice.text/action/target_entities`
- `pattern_type`
- `sentence`
- `evidence_span`
- `confidence`

### `output/condition_mapping.json`

映射表按条件类型和标准化条件组织，包含：
- `condition_raw_examples`
- `advice_count`
- `unique_advice_count`
- `advice_frequency`
- `record_examples`（含证据句和置信度）

### `output/visitor_analysis.json`

包含：
- 条件类型分布
- 景区维度分布
- 游客类型差异对比
- 重点类型（`family/elderly/couple`）即使为 0 也保留

## 最近一次运行结果（示例）

本地最近一次运行（`python main.py --extract --analyze --visualize`）统计：

- `total_advice`: **19**
- `total_travelogs`: 15
- `avg_advice_per_travelog`: 1.27
- 条件类型分布：
  - `time`: 4
  - `other`: 4
  - `route`: 3
  - `transport`: 3
  - 其余类型合计：5

> 说明：该结果会随规则参数和数据清洗策略调整而变化。

## 依赖

```text
pandas
jieba
openpyxl
matplotlib
numpy
networkx
xlsxwriter
```

安装：

```bash
pip3 install pandas jieba openpyxl matplotlib numpy networkx xlsxwriter
```

## 备注

- 若 `matplotlib` 提示缓存目录不可写，可设置：

```bash
export MPLCONFIGDIR=/tmp/matplotlib-cache
```

- 评估阶段需要手工标注文件后再运行 `--evaluate`。
