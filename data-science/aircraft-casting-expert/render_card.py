#!/usr/bin/env python3
"""
aircraft-casting-expert 工艺卡渲染器
将 diagnose.py 的结构化输出渲染为人类可读的 Markdown 工艺卡

用法：
    from render_card import render
    print(render(diagnose_result))
"""

import os
from typing import Optional

# 知识库路径（与 diagnose.py 共用同一目录）
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 诊断类型 → 渲染函数
# ============================================================

def render(result: dict) -> str:
    """将诊断结果渲染为 Markdown 工艺卡"""
    t = result.get("type", "unknown")

    if t == "defect_evaluation":
        return _render_defect(result)
    elif t == "parameter_query":
        return _render_parameters(result)
    elif t == "process_anomaly":
        return _render_process_anomaly(result)
    elif t == "mechanical_query":
        return _render_mechanical(result)
    elif t == "inspection_query":
        return _render_inspection(result)
    elif t == "terminology_query":
        return _render_terminology(result)
    elif t == "meta_guidance":
        return _render_meta_guidance(result)
    elif t == "general":
        return _render_general(result)
    else:
        return f"**未知类型**：{t}\n\n{result}"

# ============================================================
# 缺陷评估渲染
# ============================================================

def _render_defect(result: dict) -> str:
    r = result["result"]
    verdict = r.get("verdict", "未知")
    severity = r.get("severity", "")
    defect = result.get("defect", "未知缺陷")
    alloy = result.get("alloy", "未指定")
    state = result.get("state", "未指定")
    thickness = result.get("thickness")
    count = result.get("count")

    # 标题和警示
    if verdict == "拒收":
        icon = "❌"
        header = f"【诊断结论】{icon} 拒收"
        warning = f"**{defect} — 拒收**"
    elif verdict == "可接受":
        icon = "✅"
        header = f"【诊断结论】{icon} 可接受"
        warning = f"**{defect} — 在允许范围内**"
    elif verdict == "需补充信息":
        icon = "❓"
        header = f"【诊断结论】{icon} 需补充信息"
        warning = f"**{defect} — 需要更多信息才能判定**"
    else:
        icon = "⚠️"
        header = f"【诊断结论】{icon} {verdict}"
        warning = f"**{defect} — {verdict}**"

    lines = [
        f"## {header}",
        "",
        warning,
        "",
    ]

    # 基本信息
    info_lines = []
    if alloy:
        info_lines.append(f"合金：{alloy}")
    if state:
        info_lines.append(f"状态：{state}")
    if thickness:
        info_lines.append(f"铸件厚度：{thickness}mm")
    if count:
        info_lines.append(f"检出数量：{count}个")
    if info_lines:
        lines.append("**基本信息**")
        for il in info_lines:
            lines.append(f"- {il}")
        lines.append("")

    # 判定依据
    basis = r.get("basis", "")
    if basis:
        lines.append(f"**判定依据**：{basis}")
        lines.append("")

    # 标准条款
    clause = r.get("standard_clause", "")
    if clause:
        lines.append(f"📌 标准条款：{clause}")
        lines.append("")

    # 类比解释
    analogy = r.get("analogy", "")
    if analogy:
        lines.append(f"**类比**：{analogy}")
        lines.append("")

    # 处置建议
    actions = r.get("action", [])
    if actions:
        lines.append("**处置建议**：")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    # 额外信息（xray_film等）
    if r.get("xray_film"):
        lines.append(f"📷 X射线底片编号：{r['xray_film']}")

    return "\n".join(lines)

# ============================================================
# 工艺参数渲染
# ============================================================

def _render_parameters(result: dict) -> str:
    alloy = result.get("alloy", "?")
    state = result.get("state")
    r = result.get("result", {})
    clause = result.get("standard_clause", "HB5480-91 表6、表7")

    lines = [
        f"## 【工艺卡】热处理参数",
        "",
        f"**合金**：{alloy}",
    ]

    if state:
        lines.append(f"**状态**：{state}（热处理后状态）")
    lines.append("")

    # 固溶处理
    sol = r.get("solution", {})
    if sol and sol.get("temperature") not in ["未知", None]:
        lines.append("### 固溶处理（表6）")
        lines.append("")
        lines.append(f"- ▸ 固溶温度：{sol.get('temperature')}（设定值{sol.get('control_setting', '见工艺文件')}，{sol.get('tolerance', '±5°C')}）")
        lines.append(f"- ▸ 保温时间：{sol.get('time_range', '未知')}")
        if sol.get("time_note"):
            lines.append(f"  - {sol['time_note']}")
        lines.append(f"- ▸ 淬火方式：{sol.get('quenching', '未知')}")
        lines.append(f"- ▸ 转移时间：出炉到入水 {sol.get('transfer_time_limit', '?')}")
        lines.append(f"- ▸ 水温限制：{sol.get('water_temp_limit', '?')}")
        if sol.get("application"):
            lines.append(f"- ▸ 主要应用：{sol['application']}")
        lines.append("")

    # 时效处理
    aging = r.get("aging", {})
    if aging and aging.get("temperature") not in ["需查HB5446", "未知", None]:
        state_label = state or "?"
        lines.append(f"### 时效处理 {state_label}（表7）")
        lines.append("")
        lines.append(f"- ▸ 时效温度：{aging.get('temperature', '未知')}")
        lines.append(f"  - 控制器设定：{aging.get('control_setting', '见工艺文件')}，{aging.get('tolerance', '±5°C')}")
        lines.append(f"- ▸ 保温时间：{aging.get('time_range', '未知')}")
        lines.append(f"- ▸ 冷却方式：{aging.get('cooling', '空冷')}")
        if aging.get("special_requirement"):
            lines.append(f"- ▸ 特殊要求：{aging['special_requirement']}")
        if aging.get("note"):
            lines.append(f"- ⚠️ 注意：{aging['note']}")
        lines.append("")

    # 如果没有具体state，打印所有可用状态
    if not state and result.get("available_states"):
        states = result.get("available_states", [])
        sol = result.get("solution", {})
        lines.append(f"### 固溶处理（表6）")
        lines.append("")
        if sol:
            lines.append(f"- ▸ 固溶温度：{sol.get('nominal_temp', '未知')}")
            lines.append(f"- ▸ 保温时间：{sol.get('time_range', '未知')}")
            if sol.get('time_note'):
                lines.append(f"  - {sol['time_note']}")
            lines.append(f"- ▸ 淬火转移时间：{sol.get('transfer_time_limit', '?')}")
            if sol.get('water_temp_limit'):
                lines.append(f"- ▸ 淬火水温限制：{sol['water_temp_limit']}")
        lines.append("")
        # 只保留实际状态值（T5/T6/T7），过滤 note 等元数据
        real_states = [s for s in states if s in ("T5", "T6", "T7")]
        lines.append(f"### 可用时效状态：{', '.join(real_states)}")
        lines.append("")

    lines.append(f"📌 标准依据：{clause}")

    return "\n".join(lines)

# ============================================================
# 工艺异常渲染
# ============================================================

def _render_process_anomaly(result: dict) -> str:
    anomaly_type = result.get("anomaly_type", "未知")
    alloy = result.get("alloy", "未指定")
    r = result.get("result", {})
    anomaly_data = result.get("anomaly_data", {})

    error = r.get("error", "")
    if error:
        return (
            f"## 【诊断结论】❓ 需要补充信息\n\n"
            f"**问题**：{error}\n\n"
            f"请补充合金牌号后重新提问。\n"
        )

    verdict = r.get("verdict", "")
    severity = r.get("severity", "")

    # 标题
    if "温度" in anomaly_type and severity:
        lines = [
            f"## 【诊断结论】⚠️ {verdict}",
            "",
            f"**工艺异常**：{anomaly_type}",
            f"**严重程度**：{severity}",
            "",
        ]
    else:
        lines = [
            f"## 【诊断结论】⚠️ {anomaly_type}",
            "",
        ]

    # 基本信息
    if alloy:
        lines.append(f"合金：{alloy}")
    if result.get("measured_value"):
        lines.append(f"实测值：{result['measured_value']}°C")
    if r.get("upper_limit"):
        lines.append(f"规定上限：{r['upper_limit']}°C")
    if r.get("overrun", 0) > 0:
        lines.append(f"超出上限：{r['overrun']}°C")
    lines.append("")

    # 风险说明
    risk = r.get("risk", "")
    if risk:
        lines.append(f"⚠️ **风险**：{risk}")
        lines.append("")

    # 立即行动
    actions = r.get("action", [])
    if actions:
        lines.append("**立即行动**：")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    # 上报要求
    escalation = r.get("escalation", "")
    if escalation:
        lines.append(f"📌 上报要求：{escalation}")
        lines.append("")

    # 标准条款
    clause = r.get("standard_clause", "")
    if clause:
        lines.append(f"📌 标准条款：{clause}")

    return "\n".join(lines)

# ============================================================
# 力学性能渲染
# ============================================================

def _render_mechanical(result: dict) -> str:
    alloy = result.get("alloy", "?")
    state = result.get("state", "?")
    r = result.get("result", {})

    error = r.get("error")
    if error:
        return f"## 【查询结果】❌ {error}"

    levels = r.get("levels", [])
    area_label = r.get("area_label", "指定区域")
    clause = r.get("standard_clause", "HB5480-91 表3、表4")

    lines = [
        f"## 【工艺卡】力学性能要求",
        "",
        f"**合金/状态**：{alloy} / {state}",
        f"**区域类型**：{area_label}",
        "",
    ]

    if levels:
        lines.append("| 级别 | 抗拉强度σb (MPa) | 规定残余伸长应力σ0.2 (MPa) | 伸长率δ5 (%) |")
        lines.append("|------|----------------|--------------------------|-------------|")
        for rec in levels:
            lvl = rec.get("level", "?")
            ts = rec.get("tensile_strength", "—")
            ys = rec.get("yield_strength") or "—"
            el = rec.get("elongation") or "—"
            lines.append(f"| {lvl} | ≥{ts} | {ys} | ≥{el} |")
        lines.append("")

    lines.append(f"📌 标准依据：{clause}")

    return "\n".join(lines)

# ============================================================
# 检验规则渲染
# ============================================================

def _render_inspection(result: dict) -> str:
    context = result.get("context", "")
    alloy = result.get("alloy")
    state = result.get("state")
    sampling = result.get("sampling", {})

    lines = [
        "## 【工艺卡】检验要求",
        "",
    ]

    if alloy:
        lines.append(f"**合金**：{alloy}")
    if state:
        lines.append(f"**状态**：{state}")
    if context:
        lines.append(f"**问题**：{context}")
    lines.append("")

    # 通用检验要求（每批铸件）
    lines.append("### 通用检验要求（每批铸件）")
    lines.append("")
    fluo = sampling.get("fluorescence", {})
    if fluo.get("requirement"):
        lines.append(f"- ✅ {fluo['requirement']}（{fluo.get('standard_clause', '')}）")
    appear = sampling.get("appearance", {})
    if appear.get("requirement"):
        lines.append(f"- ✅ {appear['requirement']}（{appear.get('standard_clause', '')}）")
    lines.append("")

    # X射线检验抽样（分阶段）
    xray = sampling.get("xray", {})
    if xray:
        lines.append("### X射线检验抽样（HB5480-91 6.2.3）")
        lines.append("")
        lines.append("**头10批（工艺控制认可阶段）**：")
        init = xray.get("initial_production", {})
        for cls, rule in [
            ("I类", init.get("class_I", "")),
            ("II类", init.get("class_II", "")),
            ("III类", init.get("class_III", "")),
            ("IV类", init.get("class_IV", "")),
        ]:
            if rule:
                lines.append(f"  - {cls}：{rule}")
        lines.append("")
        lines.append("**10批后（连续生产稳定阶段）**：")
        normal = xray.get("normal_production", {})
        for cls, rule in [
            ("I类", normal.get("class_I", "")),
            ("II类", normal.get("class_II", "")),
            ("III类", normal.get("class_III", "")),
            ("IV类", normal.get("class_IV", "")),
        ]:
            if rule:
                lines.append(f"  - {cls}：{rule}")
        lines.append("")

    # 力学性能取样
    mech = sampling.get("mechanical", {})
    if mech:
        lines.append("### 力学性能取样（HB5480-91 6.2.4）")
        lines.append("")
        single = mech.get("single_cast_bars", {})
        if single.get("frequency"):
            lines.append(f"- **单铸试棒**：{single['frequency']}")
        if single.get("requirement"):
            lines.append(f"  - {single['requirement']}")
        if single.get("property_requirement"):
            lines.append(f"  - 力学性能标准：{single['property_requirement']}")
        attached = mech.get("attached_test_block", {})
        if attached:
            lines.append(f"- **附铸试块**：{attached.get('description', '')}")
        lines.append("- **取样部位**：按设计图样规定")
        lines.append("")

    # ZL205A T7特殊要求（由diagnose层判断，渲染层只读字段）
    need_ic = result.get("need_intergranular_corrosion", False)
    if need_ic:
        ic = sampling.get("intergranular_corrosion", {})
        if ic:
            lines.append("### ZL205A T7 特殊要求")
            lines.append("")
            lines.append(f"⚠️ **必须做晶间腐蚀倾向检验**（{ic.get('standard_clause', 'HB5255')}）")
            lines.append(f"- 方法：{ic.get('method', '')}")
            lines.append("- 结果判定：应无晶间腐蚀倾向，如有则该批铸件拒收")
            lines.append("")

    clause = sampling.get("standard_clause", "HB5480-91 6.2")
    lines.append(f"📌 标准依据：{clause}")

    return "\n".join(lines)

# ============================================================
# 术语查询渲染
# ============================================================

def _render_terminology(result: dict) -> str:
    matched = result.get("matched", {})
    context = result.get("context", "")

    lines = [
        "## 【术语解释】",
        "",
    ]

    if context:
        lines.append(f"**问题**：{context}")
        lines.append("")

    for term, data in matched.items():
        definition = data.get("definition", "暂无定义")
        lines.append(f"**{term}**")
        lines.append(f"> {definition}")

        # 类比解释
        analogy = data.get("analogy", "")
        if analogy:
            lines.append(f"> 💡 {analogy}")

        # 标准条款
        clause = data.get("standard_clause", "")
        if clause:
            lines.append(f"📌 依据：{clause}")
        lines.append("")

    return "\n".join(lines)

# ============================================================
# 元问题引导渲染
# ============================================================

def _render_meta_guidance(result: dict) -> str:
    content = result.get("content", "")
    context = result.get("context", "")

    lines = [
        "## 【引导】如何提交缺陷判定请求",
        "",
    ]

    if context:
        lines.append(f"**您的问题**：{context}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(content)

    return "\n".join(lines)

# ============================================================
# 通用查询渲染
# ============================================================

def _render_general(result: dict) -> str:
    error = result.get("error", "")
    if error:
        return f"## ❌ {error}"

    return (
        "## ❓ 无法识别问题类型\n\n"
        "请描述更具体的问题，例如：\n"
        "- \"ZL105A T6固溶温度是多少\"\n"
        "- \"X射线发现3个气孔，厚度8mm\"\n"
        "- \"固溶炉温度到545度了怎么办\"\n"
        "- \"ZL205A T7力学性能要达到多少\"\n"
    )

# ============================================================
# CLI 入口（调试用）
# ============================================================

if __name__ == "__main__":
    import json, sys
    from diagnose import diagnose

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("用法: python render_card.py <问题文本>")
        print()
        print("示例:")
        print('  python render_card.py "ZL105A T6固溶温度是多少"')
        print('  python render_card.py "X射线发现3个气孔，厚度8mm"')
        print('  python render_card.py "ZL205A T6要做成I类铸件，力学性能要达到多少"')
        sys.exit(1)

    result = diagnose(query)
    card = render(result)
    print(card)
