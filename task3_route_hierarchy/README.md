# 任务3：游览路线的层级结构挖掘

## 任务目标
1. 分析官方指南中的路线描述方式（如"上午游览A区，下午游览B区"）
2. 构建时间维度的游览层级结构（清晨→上午→中午→下午→傍晚）
3. 探索性任务：比较官方推荐路线和游客实际路线的结构差异

## 文件结构

```
task3_route_hierarchy/
├── route_parser.py          # 路线解析器
├── route_analyzer.py        # 路线对比分析器
├── main_task3.py            # 任务3主程序
├── hierarchies/             # 层级结构输出
│   ├── 九寨沟_hierarchy.json
│   ├── 九寨沟_hierarchy.png
│   ├── 故宫_hierarchy.json
│   ├── 故宫_hierarchy.png
│   ├── 黄山_hierarchy.json
│   └── 黄山_hierarchy.png
├── comparisons/             # 对比分析输出
│   ├── comparison_report.json
│   └── comparison_charts.png
└── debug/                   # 调试脚本
    ├── debug_alignment.py
    ├── debug_alignment_detailed.py
    └── test_normalization.py
```

## 脚本说明

### route_parser.py
路线解析器，支持三种不同格式的官方路线：
- **九寨沟格式**: `→`连接 + 时间范围
- **故宫格式**: 编号列表（1.2.3...）
- **黄山格式**: 多线路选择（线路一/二/三...）

解析内容：
- 路线节点序列（景点顺序）
- 时间节点（精确时间、时段）
- 交通方式
- 游览时长
- 路线类型（半日游/全日游/多日游）

### route_analyzer.py
路线对比分析器，对比官方推荐路线和游客实际路线：

**分析维度：**
| 维度 | 官方路线 | 游客路线 | 分析方法 |
|------|---------|---------|---------|
| 景点覆盖度 | 预设景点集合 | 实际游览景点 | Jaccard相似度 |
| 时间分布 | 规划时间 | 实际时间 | 时段对比 |
| 路线顺序 | 线性/推荐 | 实际路径 | LCS序列对比 |
| 游览节奏 | 规划时长 | 实际停留 | 时长对比 |

**关键指标：**
- `jaccard_similarity`: 使用标准化后的相似度
- `strict_jaccard_similarity`: 不使用标准化的相似度
- `normalization_delta`: 标准化对相似度的影响
- `set_similarity`: 集合相似度（覆盖视角）
- `sequence_similarity`: 顺序相似度（路线视角）
- `combined_similarity`: 综合相似度（0.6×顺序 + 0.4×集合）

### main_task3.py
任务3主程序，执行完整流程：
1. 加载数据（entity_results.json, data_cleaned.xlsx）
2. 解析官方路线（route_parser.py）
3. 生成层级结构（时间维度）
4. 对比分析（route_analyzer.py）
5. 生成可视化图表

## 使用方法

### 运行完整流程
```bash
python main_task3.py
```

### 单独运行各模块

```bash
# 只解析路线
python route_parser.py

# 只做对比分析
python route_analyzer.py
```

## 调试工具

### debug_alignment.py
快速查看整体对齐统计：
- 官方景点数 vs 游客POI数
- 对齐统计（已对齐/过滤/未匹配）
- 对齐详情列表
- 可疑对齐（模糊匹配相似度 < 0.85）

```bash
python debug/debug_alignment.py
```

### debug_alignment_detailed.py
详细追踪每个游客POI到官方POI的映射：
- 每个官方POI对应哪些游客POI
- 具体的对齐方法（精确匹配/标准化映射/模糊匹配）
- 未对齐和被过滤的POI列表

```bash
python debug/debug_alignment_detailed.py
```

## POI标准化映射

在 `route_analyzer.py` 中配置POI标准化映射：

```python
POI_NORMALIZATION_MAP = {
    "九寨沟": {
        "树正寨": "树正寨",  # 游客提到的真实景点，保留
        "沟口": "沟口乘车",  # 标准化为官方名称
        "高峰": None,        # 过滤噪声词
    },
    # ...
}
```

**映射类型：**
- `"别名": "标准名"` - 标准化到官方名称
- `"噪声词": None` - 过滤掉不计数
- `"景点": "景点"` - 保留为有效额外景点

## 输出说明

### 层级结构文件
- `*_hierarchy.json`: 时间维度的游览层级结构
- `*_hierarchy.png`: 层级结构可视化图

### 对比分析文件
- `comparison_report.json`: 详细的对比数据
- `comparison_charts.png`: 对比分析图表

## 核心难点

1. **命名不一致**: 游客称呼与官方名称存在差异
2. **层次关系**: 子景点与父区域的对齐判定
3. **过度对齐**: 标准化过于宽松导致相似度虚高
4. **数据质量**: 游记包含大量噪声和重复表达
5. **格式差异**: 三个景区的官方路线格式完全不同

详见各景区对比报告中的 `normalization_delta` 指标，了解标准化对结果的影响程度。
