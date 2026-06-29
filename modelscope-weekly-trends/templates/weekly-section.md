# 全量快照 Markdown 模板(v1.2 最终版)

每周一运行时,生成以下 Markdown 追加到飞书文档。
结构:TL;DR → 分板块(模型/数据/工具/论文,每板块含新增+趋势+反常+钩子) → 反常详细 → 下周重点 → 跨周追踪。

## 模板

```markdown
## {WEEK} 周一快照({DATE_RANGE})

### 📌 TL;DR
- **焦点**:{FOCUS}
- **反常**:{ANOMALY}
- **下周**:{NEXT_WEEK}

---

### 🧠 模型

#### 本周新发
| 模型 | 厂商 | 亮点 |
|---|---|---|
| **{name}** | {vendor} | {summary} |
| ... | ... | ... |

#### 趋势
- **{trend_name}** {emoji} — {evidence}

#### 反常
- **{anomaly_name}** — {what_happened}

#### 钩子
- **{hook_name}** {emoji} — {status}

---

### 📊 数据

#### 本周新发
| 数据集 | 提供方 | 亮点 |
|---|---|---|
| **{name}** | {provider} | {summary} |
| ... | ... | ... |

#### 趋势
- **{trend_name}** {emoji} — {evidence}

#### 反常
- **{anomaly_name}** — {what_happened}

#### 钩子
- **{hook_name}** {emoji} — {status}

---

### 🔧 工具 MCP

#### 核心数据
- **总数**:{total} (上期 {prev},{delta})
- **本周合作**:{partners}

#### 头部 MCP
| MCP | 提供方 | 调用量 |
|---|---|---|
| {name} | @{provider} | {usage} |
| ... | ... | ... |

#### 分类分布
{category_list}

#### 趋势
- **{trend_name}** {emoji} — {evidence}

#### 反常
- **{anomaly_name}** — {what_happened}

#### 钩子
- **{hook_name}** {emoji} — {status}

---

### 📄 论文

#### 本周热门
| 论文 | 机构 | 赞 | 亮点 |
|---|---|---|---|
| **{title}** | {org} | {likes} | {summary} |
| ... | ... | ... | ... |

#### 趋势
- **{trend_name}** {emoji} — {evidence}

#### 反常
- **{anomaly_name}** — {what_happened}

#### 钩子
- **{hook_name}** {emoji} — {status}

---

### ⚠️ 反常详细分析

1. **{anomaly_name}**
   - 【事实】...
   - 【常态】...
   - 【差异】...
   - 【推断】...

---

### 🎯 下周重点

1. ...
2. ...
3. ...

---

### 🔄 跨周追踪

| 钩子 | 来源周 | 上周状态 | 本周状态 | 结论 |
|---|---|---|---|---|
| {hook_name} | W{xx} | {last} | {this} | {verdict} |
| ... | ... | ... | ... | ... |

---
```

## 设计说明

**为什么分板块而非 16 格大表**:
- 每板块独立展开,每条信息可写完整描述(厂商/尺寸/特色)
- 飞书手机端完美适配(无横向溢出)
- 飞书全文搜索可用(图片不可搜)
- 生成耗时 0s(无需 Chrome 渲染)

**16 格思维框架保留**:每个板块内部仍按"新增/趋势/反常/钩子"4 关注点组织。
