# 渲染器架构原则

## 核心原则

**diagnose.py = 推理引擎**：从知识库提取数据、做业务判断、填充结果字典  
**render_card.py = 渲染器**：只负责把字典转成 Markdown 文本，不做任何业务判断

两者边界必须清晰。违反这条原则是专家系统最常见的 bug 来源。

## 正确模式

```
知识库(YAML) → diagnose.py(判断+填充) → result字典 → render_card.py(只格式化)
```

示例：ZL205A T7 是否需要晶间腐蚀检验

- ✅ 正确：`diagnose.py` 判断 `need_ic = (alloy == "ZL205A" and state == "T7")`，注入 result；`render_card.py` 只读 `result["need_intergranular_corrosion"]`
- ❌ 错误：`render_card.py` 自己写 `if alloy == "ZL205A" and state == "T7":`

## 症状：如何发现渲染层手敲硬编码

当发现以下任一情况时，极可能存在渲染层硬编码：
1. YAML 数据正确但输出与 YAML 不符
2. 新增字段后输出不变（诊断层注入了但渲染层没读）
3. `render_card.py` 里有 `alloy ==` 或 `state ==` 条件判断
4. 同样的业务规则散落在两处（diagnose.py 和 render_card.py 各写一遍）

## 已修复的实际案例

| 问题 | 根因 | 修复 |
|------|------|------|
| ZL205A T7 X射线表号错 | `_render_inspection()` 手敲 III/IV 类表号 | 重构为从 hb5480.yaml sampling 节读取 |
| 晶间腐蚀只在 ZL205A T7 出现 | `render_card.py` 硬编码 `if alloy == "ZL205A" and state == "T7"` | diagnose.py 注入 `need_intergranular_corrosion`，渲染层只读字段 |
| `thickness_bucket` 重复计算 | 渲染层自己算厚度区间而非读 diagnose.py 已注入的值 | diagnose.py 的 size_based 分支统一计算并注入 |
| `water_temp_limit` 缺失 | 无 state 分支只渲染3个字段，跳过淬火水温 | 补齐所有字段的渲染代码 |
| `≤≤40°C` 重复前缀 | 模板加 `≤` 前缀但 YAML 值已含符号 | YAML 值含符号，模板不加前缀 |

## 规则：渲染层禁止出现的模式

```python
# 禁止：任何业务条件判断
if alloy == "ZL205A" and state == "T7":   # ❌ 业务逻辑
if thickness < 12:                          # ❌ 派生计算

# 允许：纯粹的格式化逻辑
if result.get("error"):                    # ✅ 错误处理
if field.get("note"):                      # ✅ 元数据存在性检查
```

## 派生数据何时注入

以下数据由 diagnose.py 计算后必须注入 result，不得由渲染层重新计算：
- `thickness_bucket`：厚度区间字符串（6~12mm / ≤6mm 等）
- `need_intergranular_corrosion`：布尔值
- `available_states`：过滤后的状态列表（剔除 note 等元数据）

## 新增渲染函数的检查清单

每次在 render_card.py 新增函数或修改现有函数时：
1. 确认该函数只做格式化，不含业务判断（无 `alloy ==` / `state ==`）
2. 确认所有展示的知识内容都从 result 字典读取，不手写字符串
3. 运行端到端测试验证输出与 YAML 知识库一致
