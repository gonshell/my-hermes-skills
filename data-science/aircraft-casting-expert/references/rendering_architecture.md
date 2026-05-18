# 渲染器架构规范与已知陷阱
# 建立时间：2026-05-18
# 背景：render_card.py 曾手敲硬编码导致输出与 YAML 知识库不一致

---

## 教训：渲染器禁止手敲知识内容

### 问题现象

`_render_inspection()` 函数输出了与 HB5480-91 原文不符的检验规则：
- X射线抽样表号混淆（III类→表9，实际应→表8）
- 单铸试棒力学性能标准漏写 ZL205A 应符合 HB 962

但 `knowledge/hb5480.yaml` 中的同一条款完全正确。

### 根因

render_card.py 的 `_render_inspection()` **直接手写字符串**描述检验规则，没有从知识库检索。
这是架构层面的反模式：知识库是唯一真相来源，渲染器必须查询知识库，不得手敲。

### 正确做法

所有渲染函数的数据源规则：

```
diagnose.py（推理引擎）
    ↓ 注入结构化数据
render_card.py（渲染器）
    ↓ 只负责渲染，从不手写知识内容
    ↓ 知识必须来自 diagnose.py result["knowledge_field"]
    ↓ 或直接读取 knowledge/*.yaml（已在同一目录）
```

违反这一规则的后果：知识库正确，输出错误，调试困难（不易发现知识库是对的但渲染器在裸写）。

### 本次修复方案

1. diagnose.py 新增 `get_sampling()` 函数，在 inspection_query 分支将 sampling 数据注入 result
2. render_card.py `_render_inspection()` 重写：从 result["sampling"] 读取所有检验规则，完全废弃手写字符串

---

## 其他已知的渲染器相关陷阱

### 1. YAML 值已含前缀符号，模板不得重复加

**例子**：`water_temp_limit: "≤40°C"`（YAML值已带"≤"），模板写成 `"≤" + water_temp_limit` → `"≤≤40°C"`

**正确做法**：模板中直接使用 `water_temp_limit`，YAML 值已包含完整显示字符串

**出现位置**：render_card.py _render_parameters() 早期版本

---

### 2. 温度超温判断必须先确认合金，否则拒绝

**错误做法**：无合金时温度超 540°C → 默认按 545°C 上限判断 → 误判

**正确做法**：合金缺失时直接返回"需要补充信息"，不走默认上限逻辑

**出现位置**：diagnose.py evaluate_temp_overrun() 早期版本
