# 任务2：游览步骤的实体识别

## 任务目标
1. 定义游览程序的三类实体：景点POI、交通方式、时间节点
2. 使用Jieba分词+自定义词典，从游记中识别上述实体
3. 绘制各类实体的词频统计图（词频云或柱状图）

## 文件结构

```
task2_entity_recognition/
├── custom_dicts/           # 自定义词典
│   ├── poi/               # POI词典（按景区分类）
│   │   ├── jiuzhaigou.txt
│   │   ├── gugong.txt
│   │   └── huangshan.txt
│   ├── transport.txt      # 交通方式词典
│   └── time.txt           # 时间节点词典
├── entity_extraction.py   # 实体提取主程序
├── generate_wordcloud.py  # 词云图生成程序
├── entity_results.json    # 实体提取结果
├── output/                # 输出文件夹
│   └── wordcloud/         # 词云图
└── debug/                 # 调试脚本
    └── debug_normalize.py # 标准化调试
```

## 脚本说明

### entity_extraction.py
实体提取主程序，功能包括：
- 使用Jieba分词加载自定义词典
- 从游记中识别三类实体（POI、交通、时间）
- 提取景区特定的POI名称
- 输出结构化的实体数据

### generate_wordcloud.py
词云图生成程序，功能包括：
- 读取实体提取结果
- 过滤停用词
- 生成三类实体的词云图
- 支持中文字体显示

## 使用方法

### 1. 实体提取
```bash
python entity_extraction.py
```
输出：`entity_results.json`

### 2. 生成词云图
```bash
python generate_wordcloud.py
```
输出：`output/wordcloud/*.png`

## 自定义词典格式

### POI词典
```
景点名称 词频 词性
```
例如：
```
五花海 10000 n
镜海 9000 n
```

### 交通词典
```
步行 1000 n
观光车 800 n
```

### 时间词典
```
上午 500 t
下午 500 t
```

## 实体结果格式

```json
{
  "results": [
    {
      "scenic_spot": "九寨沟",
      "poi": ["五花海", "镜海", ...],
      "transport": {
        "basic": ["步行", "坐车"],
        "specific": ["步行", "观光车"],
        "time_distance": ["10分钟", "约5分钟"]
      },
      "time": {
        "exact": ["8:30", "9:00"],
        "relative": ["上午", "下午"],
        "duration": ["游览时间10分钟", "约1小时"]
      }
    }
  ]
}
```

## 停用词配置

在 `generate_wordcloud.py` 中配置需要过滤的停用词：
- 通用停用词：专门、上山、热门、门票等
- 景区特定停用词
