---
name: aircraft-casting-expert
description: 航空铝合金铸件工艺专家系统。接收工人自然语言问题 → 输出结构化工艺卡（Markdown/飞书消息）。基于 HB5480-91 标准，覆盖 ZL101A/ZL105A/ZL114A/ZL205A 四种合金 + T5/T6/T7 三种状态，具备诊断推理能力。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [expert-system, hb5480, aerospace, defect-diagnosis, manufacturing]
    related_skills: [technical-standard-to-beginner-guide]
---

# 航空铝合金铸件工艺专家

## Overview

输入：工人自然语言问题（如"ZL105A T6固溶温度是多少"、"X射线发现3个气孔，厚度8mm"）  
输出：结构化工艺卡（Markdown 格式，可直接发送飞书消息）

**覆盖范围：** HB5480-91 全条款  
**合金：** ZL101A / ZL105A / ZL114A / ZL205A  
**状态：** T5 / T6 / T7

## 架构

```
知识库(YAML)
  ├── hb5480.yaml        — 综合知识（分类/力学性能/sampling/缺陷分级）
  ├── parameters.yaml     — 合金×状态 → 工艺参数（固溶/时效温度+时间+淬火水温+转移时间）
  ├── defect_matrix.yaml  — 缺陷判定矩阵（零容忍/拒收/评级三类）
  ├── terminology.yaml    — 37个术语词条（含定义+类比+标准条款）
  └── process_templates.yaml — 工艺流程模板（铸造规程/检验流程/焊补矫正）

diagnose.py（推理引擎，7种路由）
  ├── defect_evaluation    — 缺陷判定（零容忍/需评级/拒收）
  ├── parameter_query      — 工艺参数查询
  ├── mechanical_query     — 力学性能查询
  ├── inspection_query     — 检验要求查询
  ├── process_anomaly      — 工艺异常（温度超标等）
  ├── terminology_query     — 术语解释
  └── general              — 无法识别

render_card.py（渲染器，7种模板）
  └── 只做格式化，不含任何业务判断
```

## 核心数据（已验证）

| 数据 | 值 | 依据 |
|------|-----|------|
| ZL205A T6 时效温度 | 170~180°C | HB5480-91 表7 |
| ZL105A T6 时效温度 | 150~160°C | HB5480-91 表7 |
| ZL205A T7 时效温度 | 见HB5446 | HB5480-91 表7 |
| ZL114A 转移时间 | ≤8s（比通用≤10s更严） | HB5480-91 表6 |
| ZL114A 淬火水温 | ≤30°C（比通用≤40°C更严） | HB5480-91 表6 |
| 零容忍缺陷 | 裂纹、冷隔、偏析（任何检出即拒收） | HB5480-91 表2 |
| 拒收缺陷 | 缩孔、任何单铸试棒力学性能不合格 | HB5480-91 |

## 7种问题类型路由

| 路由 | 触发词 | 示例问题 |
|------|--------|---------|
| defect_evaluation | 气孔/缩孔/裂纹/冷隔/偏析/针孔 | "X射线发现3个气孔，厚度8mm" |
| parameter_query | 固溶/时效/热处理/热处理制度 | "ZL105A T6固溶温度是多少" |
| mechanical_query | 力学/抗拉/屈服/伸长 | "ZL205A T6力学性能要求" |
| inspection_query | 取样/抽样/检验 | "ZL205A T7要怎么取样？" |
| process_anomaly | 温度超标/炉温 | "固溶炉温度到545度了" |
| terminology_query | T5/T6/T7/固溶/时效/淬火 等术语 | "什么是T6状态？" |
| general | 无法识别 | 落入通用回复 |

## 使用方法

```python
from diagnose import diagnose
from render_card import render

result = diagnose("ZL105A T6固溶温度是多少")
card = render(result)
print(card)
```

## 关键约束

### 渲染器不得手敲硬编码（详见 references/rendering_architecture.md）

diagnose.py 负责从知识库查询并做业务判断，填充 result 字典；render_card.py 只负责把字典格式化为 Markdown，不得包含任何 `alloy ==` / `state ==` 条件判断。

症状：YAML 数据正确但输出与 YAML 不符 → 检查 render_card.py 是否有手敲字符串。

### YAML 值已含符号

`parameters.yaml` 中 `transfer_time_limit: "≤10s"`、`water_temp_limit: "≤40°C"` 已含前缀符号，模板不得重复加 `≤`。

### available_states 需过滤

diagnose.py 返回 `aging_parameters` 下所有子键（含 `note` 元数据），render_card.py 过滤只保留 T5/T6/T7。

### 关键数据必须查原文

温度/时间/缺陷等级等数据必须从 HB5480-91 原文提取，不凭记忆。本地原文：`/root/workspace/HB5480-1991_高强度铝合金优质铸件.txt`

## 验证用测试用例（自然语言，飞书直接发送）

以下每条直接发给机器人即可验证，无需代码：

**工艺参数**
- `ZL105A T6固溶温度是多少`
- `ZL205A T6时效参数`
- `ZL114A固溶参数`

**缺陷评估**
- `X射线发现1个裂纹，厚度10mm` → 期望：拒收
- `X射线发现1个偏析，厚度20mm` → 期望：拒收
- `X射线发现10个气孔，厚度8mm` → 期望：拒收，6~12mm区间
- `X射线发现1个气孔，厚度8mm` → 期望：可接受

**温度异常**
- `固溶炉温度到545度了` → 期望：提示补充合金牌号
- `ZL105A固溶炉温度到545度了` → 期望：判断超标

**力学性能**
- `ZL205A T6力学性能要求`

**取样检验**
- `ZL205A T7要怎么取样？` → 期望：含晶间腐蚀
- `ZL105A T7要怎么取样？` → 期望：不含晶间腐蚀

**术语**
- `什么是T6状态？`

**通用**
- `铸件表面有要求吗`

## 数据修正记录

| 日期 | 问题 | 修复 |
|------|------|------|
| 2025-05-18 | II类铸件10批后X射线抽样 YAML写"表8" | 改为"表9"（原文6.2.3(b)） |

## References

- `references/rendering_architecture.md` — 渲染器架构原则（diagnose/render 边界、已修复bug清单）
