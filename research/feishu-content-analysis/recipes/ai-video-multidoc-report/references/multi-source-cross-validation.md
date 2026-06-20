# 多源交叉验证矩阵（5 doc 体系核心模式）

## 何时用这个矩阵

**触发条件**：从 5 个以上飞书 doc（混合"视频清单"和"事件流"两种类型）做综合分析时。

**5 doc 体系结构**：
| doc 类型 | 数量 | 反映 | 关键字段 |
|---|---|---|---|
| 视频清单（YouTube + B 站）| 4 | 用户兴趣（需求侧）| 播放量、UP 主、时长 |
| 事件流（结构化新闻）| 1 | 行业全景（供给侧）| 来源媒体、摘要、跨日趋势 |

## 核心洞见：两套数据讲两个故事

**经验教训**：视频 doc（用户看什么）和事件流 doc（行业发生什么）**经常不一致**。这种不一致**本身就是洞见**。

**典型 3 种错位**：

### 错位 1：行业大事 / 用户无感
- **识别方法**：事件流 doc 多源报道（来源 ≥ 3）+ 视频 doc 播放量低
- **解释**：行业关注 ≠ 用户关心（典型：监管文件、IPO 进展）
- **报告处理**：在对应章节标注"行业重要 / 用户无感"，不强行吹

### 错位 2：用户关心 / 行业无报道
- **识别方法**：视频 doc 高播放（≥ 100 万）+ 事件流 doc 0 报道
- **解释**：用户兴趣 vs 行业叙事脱节（典型：UCG 内容、蹭热点内容）
- **报告处理**：标注"用户热度 / 行业无跟踪"，可能是泡沫或前沿

### 错位 3：双方共同关注
- **识别方法**：事件流多源 + 视频高播放
- **解释**：真热点
- **报告处理**：作为强证据，洞见 + 反方配套

## 交叉验证矩阵（实操）

```python
# 输入：5 doc 解析后的数据
# 视频 doc 数据格式: [{title, channel, views, duration, upload_date, ...}, ...]
# 事件流 doc 数据格式: [{date, index, title, source, summary, ...}, ...]

# 步骤 1：提取视频 doc 的"高播放视频标题关键词"
video_hot_keywords = Counter()
for item in video_items:
    for kw in extract_keywords(item['title']):  # 提取专有名词
        if parse_views(item['views']) > 500000:  # 高播放阈值
            video_hot_keywords[kw] += 1

# 步骤 2：提取事件流 doc 的"高报道事件标题关键词"
event_hot_keywords = Counter()
for event in event_items:
    for kw in extract_keywords(event['title']):
        if event['source'].count('/') >= 2:  # 多源报道阈值
            event_hot_keywords[kw] += 1

# 步骤 3：交叉矩阵
matrix = {}
for kw in set(video_hot_keywords) | set(event_hot_keywords):
    matrix[kw] = {
        'video_score': video_hot_keywords.get(kw, 0),
        'event_score': event_hot_keywords.get(kw, 0),
        'gap': video_hot_keywords.get(kw, 0) - event_hot_keywords.get(kw, 0)
    }

# 步骤 4：分桶
hot_in_both = {k: v for k, v in matrix.items() if v['video_score'] >= 3 and v['event_score'] >= 3}
hot_only_video = {k: v for k, v in matrix.items() if v['video_score'] >= 3 and v['event_score'] == 0}
hot_only_event = {k: v for k, v in matrix.items() if v['video_score'] == 0 and v['event_score'] >= 3}
```

## 错位案例库

| 关键词 | 视频热度 | 事件流热度 | 错位类型 | 解释 |
|---|---|---|---|---|
| `Anthropic Fable 5` 出口管制 | 低（视频谈"主动受限"）| 高（多源 4+）| 错位 1 | 行业关注政策面，用户只关心产品 |
| `DeepSeek 解除限制` | 高（135 条 B 站视频）| 低（仅少数报道）| 错位 2 | UCG 蹭热点内容，行业不严肃跟踪 |
| `Kimi K2.7` 性能 | 中等 | 高（多源 5+）| 错位 3 部分 | 真热点，但用户讨论偏向"测评"而非"参数" |
| `Apple Siri AI` | 中等 | 中等 | 错位 3 | 真热点，双向关注 |

## 写入报告的位置

**每章"事实段"末尾加交叉验证小结**：

```markdown
## §3 技术

**事实段**（3.1-3.4）：...

**5 doc 交叉验证**：
- 真热点（视频 + 事件流均高）：Kimi K2.7 / Apple Siri AI
- 行业大事但用户无感：Anthropic Fable 5 出口管制（事件流多源 / 视频 0）
- 用户关心但行业无报道：DeepSeek 解除限制（视频 135 条 / 事件流 1）
```

**或在附录 B 加 1 张矩阵表**：

```markdown
## 附录 B 5 doc 交叉验证矩阵

| 关键词 | 视频 doc 热度 | 事件流 doc 热度 | 错位类型 | 写入位置 |
|---|---|---|---|---|
| Anthropic Fable 5 | 中（晚间档 + 早间档各 1 条）| 高（事件流 4 源）| 错位 1 | §3.3 + §6.x 涌现"AI 出口管制" |
| DeepSeek 解除限制 | 高（B 站 doc 135 条）| 低 | 错位 2 | §6.x 涌现"UGC 蹭热点" |
| ... |
```

## 为什么这个模式是核心

**用户偏好**："综合性报告" = 跨数据源整合，不是单源深挖。

**如果只读视频 doc**：看到的是"用户兴趣"——可能严重偏向 UCG、蹭热点、低质量内容。
**如果只读事件流 doc**：看到的是"行业全景"——但不知道用户关心什么。
**两个一起读**：才能区分"真热点"、"泡沫"、"前沿"。

**不写交叉验证 = 报告失去 50% 信息价值**。这是 v1-v9 报告严重失衡的根因。

## 跟 Step 4 写章节的配合

```python
# Step 4 写 §3 技术的"事实段"时
for event in high_priority_events_in_chapter:
    video_evidence = find_video_evidence(event, all_video_items)
    if video_evidence:
        # 双向都有证据
        write_fact(event, video_evidence, strong_evidence=True)
    else:
        # 仅事件流 doc 有
        write_fact(event, source='事件流 doc', strong_evidence=False, note='视频 doc 无相关')
```

## 实战限制

- **关键词提取**要简单（专有名词、模型名、机构名），别上 NLP——大模型下经常误判
- **阈值不能硬编码**：高播放阈值（500 万）需要根据数据规模调整。如果只有 50 条视频，10 万播放就算高播放
- **错位 1 报告价值高**：用户可能没意识到某个行业大事正在发生（监管 / 政策）
- **错位 2 报告价值低**：UCG 蹭热点是常态，不值得每个都报
- **错位 3 报告价值最高**：双向证据的洞见最可信
