#!/usr/bin/env python3
"""
aircraft-casting-expert 工艺卡渲染器（修正版）
将 diagnose.py 的结构化输出渲染为人类可读的 Markdown 工艺卡

用法：
    from render_card import render
    print(render(diagnose_result))
"""

from typing import Optional

def render(result: dict) -> str:
    t = result.get("type", "unknown")
    if t == "defect_evaluation":   return _render_defect(result)
    elif t == "parameter_query":    return _render_parameters(result)
    elif t == "process_anomaly":   return _render_process_anomaly(result)
    elif t == "mechanical_query":  return _render_mechanical(result)
    elif t == "inspection_query":   return _render_inspection(result)
    elif t == "general":           return _render_general(result)
    else: return f"**未知类型**：{t}\n\n{result}"

def _render_defect(result: dict) -> str:
    r = result["result"]
    verdict = r.get("verdict", "未知")
    defect = result.get("defect", "未知缺陷")
    alloy = result.get("alloy", "未指定")
    state = result.get("state", "未指定")
    thickness = result.get("thickness")
    count = result.get("count")
    icons = {"拒收": ("❌", "拒收"), "可接受": ("✅", "在允许范围内"), "需补充信息": ("❓", "需要更多信息")}
    icon, suffix = icons.get(verdict, ("⚠️", verdict))
    lines = [f"## 【诊断结论】{icon} {verdict}", "", f"**{defect} — {suffix}**", ""]
    info = []
    if alloy: info.append(f"合金：{alloy}")
    if state: info.append(f"状态：{state}")
    if thickness: info.append(f"铸件厚度：{thickness}mm")
    if count: info.append(f"检出数量：{count}个")
    if info: lines += ["**基本信息**"] + [f"- {x}" for x in info] + [""]
    if r.get("basis"): lines += [f"**判定依据**：{r['basis']}", ""]
    if r.get("standard_clause"): lines += [f"📌 标准条款：{r['standard_clause']}", ""]
    if r.get("analogy"): lines += [f"**类比**：{r['analogy']}", ""]
    if r.get("action"):
        lines.append("**处置建议**：")
        lines += [f"- {a}" for a in r["action"]]
        lines.append("")
    if r.get("xray_film"): lines.append(f"📷 X射线底片编号：{r['xray_film']}")
    return "\n".join(lines)

def _render_parameters(result: dict) -> str:
    alloy = result.get("alloy", "?")
    state = result.get("state")
    r = result.get("result", {})
    clause = result.get("standard_clause", "HB5480-91 表6、表7")
    lines = [f"## 【工艺卡】热处理参数", "", f"**合金**：{alloy}"]
    if state: lines.append(f"**状态**：{state}（热处理后状态）")
    lines.append("")
    sol = r.get("solution", {})
    if sol and sol.get("temperature") not in ["未知", None]:
        lines += ["### 固溶处理（表6）", ""]
        lines.append(f"- ▸ 固溶温度：{sol.get('temperature')}（设定值{sol.get('control_setting', '见工艺文件')}，{sol.get('tolerance', '±5°C')}）")
        lines.append(f"- ▸ 保温时间：{sol.get('time_range', '未知')}")
        if sol.get("time_note"): lines.append(f"  - {sol['time_note']}")
        lines.append(f"- ▸ 淬火方式：{sol.get('quenching', '未知')}")
        lines.append(f"- ▸ 转移时间：出炉到入水 {sol.get('transfer_time_limit', '?')}")
        lines.append(f"- ▸ 水温限制：{sol.get('water_temp_limit', '?')}")
        if sol.get("application"): lines.append(f"- ▸ 主要应用：{sol['application']}")
        lines.append("")
    aging = r.get("aging", {})
    if aging and aging.get("temperature") not in ["需查HB5446", "未知", None]:
        sl = state or "?"
        lines += [f"### 时效处理 {sl}（表7）", ""]
        lines.append(f"- ▸ 时效温度：{aging.get('temperature', '未知')}")
        lines.append(f"  - 控制器设定：{aging.get('control_setting', '见工艺文件')}，{aging.get('tolerance', '±5°C')}")
        lines.append(f"- ▸ 保温时间：{aging.get('time_range', '未知')}")
        lines.append(f"- ▸ 冷却方式：{aging.get('cooling', '空冷')}")
        if aging.get("special_requirement"): lines.append(f"- ▸ 特殊要求：{aging['special_requirement']}")
        if aging.get("note"): lines.append(f"- ⚠️ 注意：{aging['note']}")
        lines.append("")
    if alloy == "ZL205A" and state == "T7":
        lines += ["### 时效处理 T7（表7）", "", "⚠️ **表7未规定具体值，需查HB5446或订货文件**", ""]
    if not state and result.get("available_states"):
        states = result.get("available_states", [])
        sol = result.get("solution", {})
        lines += [f"### 固溶处理（表6）", ""]
        if sol:
            lines.append(f"- ▸ 固溶温度：{sol.get('nominal_temp', '未知')}")
            lines.append(f"- ▸ 保温时间：{sol.get('time_range', '未知')}")
            lines.append(f"- ▸ 淬火转移时间：≤{sol.get('transfer_time_limit', '?')}")
        lines += ["", f"### 可用时效状态：{', '.join(states)}", ""]
    lines.append(f"📌 标准依据：{clause}")
    return "\n".join(lines)

def _render_process_anomaly(result: dict) -> str:
    anomaly_type = result.get("anomaly_type", "未知")
    alloy = result.get("alloy", "未指定")
    r = result.get("result", {})
    if r.get("error"):
        return (f"## 【诊断结论】❓ 需要补充信息\n\n"
                f"**问题**：{r['error']}\n\n请补充合金牌号后重新提问。\n")
    verdict = r.get("verdict", "")
    severity = r.get("severity", "")
    if "温度" in anomaly_type and severity:
        lines = [f"## 【诊断结论】⚠️ {verdict}", "", f"**工艺异常**：{anomaly_type}", f"**严重程度**：{severity}", ""]
    else:
        lines = [f"## 【诊断结论】⚠️ {anomaly_type}", ""]
    if alloy: lines.append(f"合金：{alloy}")
    if result.get("measured_value"): lines.append(f"实测值：{result['measured_value']}°C")
    if r.get("upper_limit"): lines.append(f"规定上限：{r['upper_limit']}°C")
    if r.get("overrun", 0) > 0: lines.append(f"超出上限：{r['overrun']}°C")
    lines.append("")
    if r.get("risk"): lines += [f"⚠️ **风险**：{r['risk']}", ""]
    if r.get("action"):
        lines.append("**立即行动**：")
        lines += [f"- {a}" for a in r["action"]]
        lines.append("")
    if r.get("escalation"): lines += [f"📌 上报要求：{r['escalation']}", ""]
    if r.get("standard_clause"): lines.append(f"📌 标准条款：{r['standard_clause']}")
    return "\n".join(lines)

def _render_mechanical(result: dict) -> str:
    alloy = result.get("alloy", "?")
    state = result.get("state", "?")
    r = result.get("result", {})
    if r.get("error"): return f"## 【查询结果】❌ {r['error']}"
    levels = r.get("levels", [])
    area_label = r.get("area_label", "指定区域")
    clause = r.get("standard_clause", "HB5480-91 表3、表4")
    lines = [f"## 【工艺卡】力学性能要求", "", f"**合金/状态**：{alloy} / {state}", f"**区域类型**：{area_label}", ""]
    if levels:
        lines += ["| 级别 | 抗拉强度σb (MPa) | 规定残余伸长应力σ0.2 (MPa) | 伸长率δ5 (%) |",
                  "|------|----------------|--------------------------|-------------|"]
        for rec in levels:
            ts = rec.get("tensile_strength", "—")
            ys = rec.get("yield_strength") or "—"
            el = rec.get("elongation") or "—"
            lines.append(f"| {rec.get('level','?')} | ≥{ts} | {ys} | ≥{el} |")
        lines.append("")
    lines.append(f"📌 标准依据：{clause}")
    return "\n".join(lines)

# ============================================================
# 检验规则渲染（从 hb5480.yaml 检索，不再手写字符串）
# ============================================================
def _render_inspection(result: dict) -> str:
    import yaml, os
    context = result.get("context", "")
    alloy = result.get("alloy")
    state = result.get("state")

    # ── 从 hb5480.yaml 加载取样规则 ──────────────────────────
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    hb5480_path = os.path.join(skill_dir, "knowledge", "hb5480.yaml")
    with open(hb5480_path, encoding="utf-8") as f:
        hb = yaml.safe_load(f)
    sampling = hb.get("sampling", {})
    xray = sampling.get("xray", {})
    mechanical = sampling.get("mechanical", {})
    # ─────────────────────────────────────────────────────────

    lines = ["## 【工艺卡】检验要求", ""]
    if alloy: lines.append(f"**合金**：{alloy}")
    if state: lines.append(f"**状态**：{state}")
    if context: lines.append(f"**问题**：{context}")
    lines.append("")

    lines += ["### 通用检验要求（每批铸件）", ""]
    fluo = sampling.get("fluorescence", {})
    lines.append(f"- ✅ 每批所有铸件荧光检查（{fluo.get('standard_clause', 'HB5480-91 6.2.2')}）")
    appear = sampling.get("appearance", {})
    lines.append(f"- ✅ 每批所有铸件外观和尺寸检查（{appear.get('standard_clause', 'HB5480-91 6.2.5')}）")
    lines.append("")

    lines += ["### X射线检验抽样（HB5480-91 6.2.3）", ""]
    xray_initial = xray.get("initial_production", {})
    lines.append("**阶段一：头10批（铸造工艺控制认可后）**")
    lines.append(f"- I类铸件：{xray_initial.get('class_I', '每批所有铸件全面检查')}")
    lines.append(f"- II类铸件：{xray_initial.get('class_II', '每批所有铸件全面检查')}")
    lines.append(f"- III类铸件：{xray_initial.get('class_III', '按表8规定抽取样件检查')}")
    lines.append(f"- IV类铸件：{xray_initial.get('class_IV', '按表9规定抽取样件检查')}")
    lines.append("")

    xray_normal = xray.get("normal_production", {})
    lines.append("**阶段二：连续生产10批证明质量稳定后**")
    lines.append(f"- I类铸件：{xray_normal.get('class_I', '每批所有铸件全面检查')}")
    lines.append(f"- II类铸件：{xray_normal.get('class_II', '按表8规定抽取样件检查')}")
    lines.append(f"- III类铸件：{xray_normal.get('class_III', '按表9规定抽取样件检查')}")
    lines.append(f"- IV类铸件：{xray_normal.get('class_IV', '除非订货文件规定放弃X射线照相检查')}")
    lines.append("")

    lines += ["### 力学性能取样（HB5480-91 6.2.4）", ""]
    single = mechanical.get("single_cast_bars", {})
    lines.append(f"- **单铸试棒**：{single.get('frequency', '每个熔炼炉次至少两个单铸试棒')}")
    lines.append(f"  - {single.get('requirement', '同炉熔炼+同炉热处理')}")
    prop_req = single.get('property_requirement', 'ZL101A/105A/114A符合表3的2级；ZL205A符合HB 962')
    lines.append(f"  - 力学性能标准：{prop_req}")
    lines.append("- **大铸件（>50kg）**：每个熔炼炉次≥1个附铸试块，截面尺寸与铸件取样部位相同")
    lines.append("- **取样部位**：按设计图样规定")
    lines.append("")

    if alloy == "ZL205A" and state == "T7":
        lines += ["### ZL205A T7 特殊要求", ""]
        lines.append("⚠️ **必须做晶间腐蚀倾向检验**（HB5255）")
        lines.append("- 热处理后按HB5480-91 5.7检查，应无晶间腐蚀倾向")
        lines.append("- 如有晶间腐蚀倾向，该批铸件拒收")
        lines.append("")
        lines.append("⚠️ **时效参数**：表7对ZL205A T7未规定具体值，需查HB5446或订货文件")
        lines.append("")

    clause = xray.get("standard_clause", "HB5480-91 6.2.3")
    lines.append(f"📌 标准依据：{clause}, HB/Z60, HB/Z61, GB 228")
    return "\n".join(lines)

def _render_general(result: dict) -> str:
    if result.get("error"): return f"## ❌ {result['error']}"
    return ("## ❓ 无法识别问题类型\n\n"
            "请描述更具体的问题，例如：\n"
            "- \"ZL105A T6固溶温度是多少\"\n"
            "- \"X射线发现3个气孔，厚度8mm\"\n"
            "- \"固溶炉温度到545度了怎么办\"\n"
            "- \"ZL205A T7力学性能要达到多少\"\n")

if __name__ == "__main__":
    import sys
    from diagnose import diagnose
    if len(sys.argv) > 1:
        result = diagnose(" ".join(sys.argv[1:]))
        print(render(result))
    else:
        print("用法: python render_card.py <问题文本>")
