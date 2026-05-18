#!/usr/bin/env python3
"""
aircraft-casting-expert 诊断推理引擎
基于 HB5480-91 标准，对航空铝合金铸件问题进行诊断推理

用法：
    result = diagnose("ZL105A T6固溶温度是多少")
    result = diagnose("X射线发现3个气孔，厚度8mm")
    result = diagnose("固溶炉温度到545度了")
"""

import re
import yaml
from pathlib import Path
from typing import Optional

# ============================================================
# 知识库加载
# ============================================================

SKILL_DIR = Path(__file__).parent
KB_DIR = SKILL_DIR / "knowledge"

def load_yaml(name: str) -> dict:
    with open(KB_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)

# 延迟加载知识库（首次使用时才加载）
_kb: Optional[dict] = None
_params: Optional[dict] = None
_defects: Optional[dict] = None
_process: Optional[dict] = None
_terms: Optional[dict] = None

def get_kb():
    global _kb
    if _kb is None:
        _kb = load_yaml("hb5480.yaml")
    return _kb

def get_params():
    global _params
    if _params is None:
        _params = load_yaml("parameters.yaml")
    return _params

def get_sampling():
    """从 hb5480.yaml 检索取样规程（6.2节）"""
    kb = get_kb()
    return kb.get("sampling", {})

def get_defects():
    global _defects
    if _defects is None:
        _defects = load_yaml("defect_matrix.yaml")
    return _defects

def get_process():
    global _process
    if _process is None:
        _process = load_yaml("process_templates.yaml")
    return _process

def get_terms():
    global _terms
    if _terms is None:
        _terms = load_yaml("terminology.yaml")
    return _terms

# ============================================================
# 合金牌号识别
# ============================================================

ALLOY_PATTERNS = {
    "ZL101A": ["ZL101A", "101A"],
    "ZL105A": ["ZL105A", "105A"],
    "ZL114A": ["ZL114A", "114A"],
    "ZL205A": ["ZL205A", "205A"],
}

STATE_PATTERNS = {
    "T5": ["T5"],
    "T6": ["T6"],
    "T7": ["T7"],
}

def extract_alloy(text: str) -> Optional[str]:
    """从文本中提取合金牌号"""
    for alloy, patterns in ALLOY_PATTERNS.items():
        for p in patterns:
            if p in text:
                return alloy
    return None

def extract_state(text: str) -> Optional[str]:
    """从文本中提取热处理状态"""
    for state, patterns in STATE_PATTERNS.items():
        for p in patterns:
            if p in text:
                return state
    return None

# ============================================================
# 症状解析
# ============================================================

DEFECT_KEYWORDS = {
    "裂纹": ["裂纹", "开裂", "裂口"],
    "冷隔": ["冷隔", "冷纹", "接缝"],
    "偏析": ["偏析", "成分不均"],
    "缩孔": ["缩孔", "缩松", "内部疏松"],
    "海绵状疏松": ["海绵状疏松", "蜂窝状疏松", "树枝状疏松"],
    "夹杂物": ["夹杂物", "夹渣", "异物", "砂眼"],
    "气孔": ["气孔", "内部有孔", "气泡"],
    "针孔": ["针孔", "密集小孔", "微小气孔"],
}

PROCESS_KEYWORDS = {
    "温度超标_轻微": ["温度偏高", "炉温超", "温度到", "到535", "到540", "稍高"],
    "温度超标_严重": ["严重超温", "过烧", "温度过高", "550"],
    "保温时间不足": ["保温时间不够", "时间太短", "提前出炉", "保温不足"],
    "淬火转移时间超限": ["转移时间太长", "出炉到入水慢", "淬火延迟", "转移时间"],
    "水温超标": ["水温太高", "水槽温度", "水温超标"],
}

def extract_defect(text: str) -> Optional[str]:
    """从文本中提取缺陷类型"""
    for defect, keywords in DEFECT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return defect
    return None

def extract_process_anomaly(text: str) -> Optional[str]:
    """从文本中提取工艺异常类型"""
    for anomaly, keywords in PROCESS_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return anomaly
    return None

def extract_thickness(text: str) -> Optional[float]:
    """从文本中提取厚度（mm）"""
    patterns = [
        r"厚度\s*[为是]?\s*(\d+\.?\d*)\s*mm",
        r"(\d+\.?\d*)\s*mm\s*厚",
        r"壁厚\s*[为是]?\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*毫米",
        r"(\d+\.?\d*)\s*mm",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return float(m.group(1))
    return None

def extract_defect_count(text: str) -> Optional[int]:
    """从文本中提取缺陷数量"""
    m = re.search(r"(\d+)\s*[个处]?\s*(气孔|缩孔|针孔|缺陷)", text)
    if m:
        return int(m.group(1))
    return None

def extract_temperature(text: str) -> Optional[float]:
    """从文本中提取温度（°C）"""
    m = re.search(r"(\d+)\s*[度°C]", text)
    if m:
        return float(m.group(1))
    return None

def extract_time(text: str) -> Optional[float]:
    """从文本中提取时间（小时）"""
    m = re.search(r"(\d+\.?\d*)\s*[小h时]", text)
    if m:
        return float(m.group(1))
    return None

# ============================================================
# 缺陷判定
# ============================================================

def get_defect_severity(defect_type: str) -> str:
    """判断缺陷严重程度"""
    defects = get_defects()
    categories = defects.get("defect_categories", {})

    for cat_name in ["zero_tolerance", "reject_if_found", "size_based"]:
        cat = categories.get(cat_name, {})
        defect_list = cat.get("defects", [])
        if defect_type in defect_list:
            if cat_name == "zero_tolerance":
                return "zero_tolerance"
            elif cat_name == "reject_if_found":
                return "reject_if_found"
            else:
                return "size_based"
    return "unknown"

def evaluate_defect(defect_type: str, thickness: float = None,
                     count: int = None, alloy: str = None, state: str = None) -> dict:
    """
    评估缺陷是否合格
    返回：{verdict, severity, basis, action, standard_clause}
    """
    defects_kb = get_defects()
    defect_entry = defects_kb.get("defects", {}).get(defect_type, {})
    severity = get_defect_severity(defect_type)

    # 零容忍缺陷
    if severity == "zero_tolerance":
        return {
            "verdict": "拒收",
            "severity": "零容忍",
            "defect_type": defect_type,
            "basis": f"{defect_type}为HB5480-91表2零容忍缺陷，任何含量均不允许",
            "action": [
                "该铸件判为不合格，隔离存放",
                "填写不合格品处理单",
                "同一批次扩大抽样检查",
            ],
            "standard_clause": defect_entry.get("standard_clause", "HB5480-91 4.4.1"),
            "analogy": defect_entry.get("rationale", ""),
        }

    # 发现即拒收缺陷
    if severity == "reject_if_found":
        return {
            "verdict": "拒收",
            "severity": "拒收项",
            "defect_type": defect_type,
            "basis": f"{defect_type}在HB5480-91表2中一旦检出即拒收",
            "action": [
                "该铸件判为不合格，隔离存放",
                "填写不合格品处理单",
                "同一批次扩大抽样检查",
            ],
            "standard_clause": defect_entry.get("standard_clause", "HB5480-91 5.2"),
            "xray_film": defect_entry.get("xray_film", ""),
        }

    # 需评级的缺陷（气孔、针孔）
    if severity == "size_based":
        if thickness is None:
            return {
                "verdict": "需补充信息",
                "severity": "需评级",
                "defect_type": defect_type,
                "basis": "气孔/针孔需根据铸件厚度和缺陷数量按表2评级",
                "action": ["请提供铸件厚度（mm）和检出缺陷数量"],
                "standard_clause": "HB5480-91 表2",
            }

        # 根据厚度确定评级区间
        if thickness <= 6:
            key = "film_thickness_6mm"
        elif thickness <= 12:
            key = "film_thickness_6to12"
        elif thickness <= 20:
            key = "film_thickness_12to20"
        else:
            key = "film_thickness_20to50"

        limit_str = defect_entry.get(key, 0)

        # 处理复合字符串如"圆形1/长条形1"
        if isinstance(limit_str, str) and "/" in limit_str:
            # 取较严格的值作为上限
            nums = [int(re.search(r"\d+", s).group()) for s in limit_str.split("/")]
            limit = min(nums) if defect_type == "针孔" else (nums[0] if nums else 0)
        else:
            limit = int(limit_str) if limit_str else 0

        if count is None:
            return {
                "verdict": "需补充信息",
                "severity": "需评级",
                "defect_type": defect_type,
                "thickness": thickness,
                "thickness_range_key": key.replace("film_thickness_", ""),
                "limit": limit,
                "basis": f"厚度{thickness}mm（{key.replace('film_thickness_','').replace('to','~')}mm区间）",
                "action": [f"请提供检出{defect_type}数量，当前允许≤{limit}个"],
                "standard_clause": defect_entry.get("standard_clause", "HB5480-91 表2"),
            }

        if count > limit:
            bucket_map = {
                "film_thickness_6mm": "≤6mm",
                "film_thickness_6to12": "6~12mm",
                "film_thickness_12to20": "12~20mm",
                "film_thickness_20to50": "20~50mm",
            }
            bucket = bucket_map.get(key, "")
            return {
                "verdict": "拒收",
                "severity": "超标",
                "defect_type": defect_type,
                "thickness": thickness,
                "thickness_bucket": bucket,
                "count_found": count,
                "limit": limit,
                "basis": f"检出{count}个，超过表2允许的{limit}个（厚度区间{bucket}）",
                "action": [
                    "该铸件判为不合格，隔离存放",
                    "填写不合格品处理单",
                    "同一批次扩大抽样检查",
                ],
                "standard_clause": defect_entry.get("standard_clause", "HB5480-91 表2"),
            }
        else:
            bucket_map = {
                "film_thickness_6mm": "≤6mm",
                "film_thickness_6to12": "6~12mm",
                "film_thickness_12to20": "12~20mm",
                "film_thickness_20to50": "20~50mm",
            }
            bucket = bucket_map.get(key, "")
            return {
                "verdict": "可接受",
                "severity": "合格",
                "defect_type": defect_type,
                "thickness": thickness,
                "thickness_bucket": bucket,
                "count_found": count,
                "limit": limit,
                "basis": f"检出{count}个，在表2允许范围≤{limit}个内（厚度区间{bucket}）",
                "action": ["通过验收"],
                "standard_clause": defect_entry.get("standard_clause", "HB5480-91 表2"),
            }

    return {
        "verdict": "无法判定",
        "severity": "未知",
        "defect_type": defect_type,
        "basis": f"未知缺陷类型：{defect_type}",
        "action": ["请咨询工艺工程师"],
        "standard_clause": "",
    }

# ============================================================
# 工艺参数查询
# ============================================================

def query_heat_treatment(alloy: str, state: str) -> dict:
    """查询热处理工艺参数"""
    params = get_params()

    # 固溶参数
    sol = params.get("solution_parameters", {}).get(alloy, {})
    # 时效参数
    aging_all = params.get("aging_parameters", {}).get(alloy, {})
    aging = aging_all.get(state, {})

    result = {
        "alloy": alloy,
        "state": state,
        "solution": {
            "temperature": sol.get("nominal_temp", "未知"),
            "control_setting": sol.get("control_temp", "未知"),
            "tolerance": sol.get("tolerance", "未知"),
            "time_range": sol.get("time_range", "未知"),
            "time_note": sol.get("time_note", ""),
            "quenching": sol.get("quenching", "未知"),
            "water_temp_limit": sol.get("water_temp_limit", "未知"),
            "transfer_time_limit": sol.get("transfer_time_limit", "未知"),
            "state_after": sol.get("state_after", ""),
            "application": sol.get("application", ""),
        },
        "aging": {
            "temperature": aging.get("nominal_temp", "需查HB5446"),
            "control_setting": aging.get("control_temp", "需查HB5446"),
            "tolerance": aging.get("tolerance", "未知"),
            "time_range": aging.get("time_range", "需查HB5446"),
            "cooling": aging.get("cooling", "空冷"),
            "special_requirement": aging.get("special_requirement", ""),
        },
        "standard_clause": "HB5480-91 表6、表7",
    }

    # 添加备注
    aging_note = aging_all.get("note", "")
    if aging_note:
        result["aging"]["note"] = aging_note

    return result

def evaluate_temp_overrun(alloy: str, temp: float, context: str = "") -> dict:
    """评估温度超标程度"""
    params = get_params()

    if alloy:
        sol = params.get("solution_parameters", {}).get(alloy, {})
        nominal = sol.get("nominal_temp", "")
    else:
        nominal = ""

    # 提取上限
    if not alloy:
        return {
            "alloy": None,
            "measured_temp": temp,
            "error": "需要提供合金牌号才能判断是否超温（如ZL105A上限520~530°C，ZL114A上限535~545°C）",
        }
    m = re.search(r"(\d+)~\d+", nominal) if nominal else None
    if m:
        upper_limit = float(m.group(1))
    else:
        m2 = re.search(r"(\d+)", nominal) if nominal else None
        upper_limit = float(m2.group(1)) if m2 else 545

    overrun = temp - upper_limit

    if overrun > 10 or temp > 550:
        severity = "严重（过烧风险）"
        verdict = "必须立即停止"
        action = [
            "立即关炉，停止加热",
            "该炉次铸件标记'待评估'，不得流入下道工序",
            "查明原因：热电偶故障？设定温度错误？炉温均匀性差？",
            "由工艺工程师和质检人员共同评估组织状态",
            "可能结果：降级使用或整炉报废",
        ]
        escalation = "必须上报"
        risk = "过烧导致晶界氧化，强度永久下降，不可挽救"
    elif overrun > 0:
        severity = "轻微"
        verdict = "记录，评估"
        action = [
            "记录超温情况（炉号、温度、持续时间）",
            "评估对组织和性能的影响",
            "决定是否降级使用",
        ]
        escalation = "由工艺工程师判断"
        risk = "可能影响性能，建议做力学性能抽样验证"
    else:
        severity = "正常"
        verdict = "未超标"
        action = ["在工艺范围内"]
        escalation = "无需上报"
        risk = ""

    return {
        "alloy": alloy,
        "measured_temp": temp,
        "upper_limit": upper_limit,
        "overrun": overrun,
        "severity": severity,
        "verdict": verdict,
        "action": action,
        "escalation": escalation,
        "risk": risk,
        "context": context,
        "standard_clause": "HB5480-91 4.8.1, HB 5446",
    }

# ============================================================
# 力学性能查询
# ============================================================

def query_mechanical_properties(alloy: str, state: str,
                                  designated: bool = True,
                                  level: int = None) -> dict:
    """查询力学性能要求"""
    kb = get_kb()
    mech = kb.get("mechanical_properties", {})

    section = mech.get("designated_area" if designated else "nondesignated_area", {})
    alloy_data = section.get(alloy, {})
    state_data = alloy_data.get(state, [])

    if not state_data:
        return {
            "alloy": alloy,
            "state": state,
            "designated": designated,
            "error": f"未找到{alloy} {state}的力学性能数据",
        }

    if level is not None:
        # 筛选指定级别
        filtered = [r for r in state_data if r.get("level") == level]
        records = filtered if filtered else state_data
    else:
        records = state_data

    return {
        "alloy": alloy,
        "state": state,
        "designated": designated,
        "area_label": "指定区域" if designated else "非指定区域",
        "levels": records,
        "standard_clause": "HB5480-91 表3（指定区域）或表4（非指定区域）",
    }

# ============================================================
# 主诊断函数
# ============================================================

def diagnose(text: str) -> dict:
    """
    主诊断函数

    参数：
        text: 工人描述的自然语言问题

    返回结构化诊断结果：
        {
            "type": "defect_evaluation" | "parameter_query" | "process_anomaly" |
                    "mechanical_query" | "inspection_query" | "general",
            "alloy": "ZL105A",
            "state": "T6",
            "result": { ... 具体结果 ... }
        }
    """
    text_lower = text.lower()
    alloy = extract_alloy(text)
    state = extract_state(text)
    defect = extract_defect(text)
    anomaly = extract_process_anomaly(text)
    thickness = extract_thickness(text)
    count = extract_defect_count(text)
    temperature = extract_temperature(text)
    time_val = extract_time(text)

    # 判断问题类型
    if defect:
        # 缺陷判定
        eval_result = evaluate_defect(defect, thickness, count, alloy, state)
        return {
            "type": "defect_evaluation",
            "alloy": alloy,
            "state": state,
            "defect": defect,
            "thickness": thickness,
            "count": count,
            "result": eval_result,
        }

    elif anomaly:
        # 工艺异常
        params_p = get_params()
        defect_kb = get_defects()
        anomaly_data = defect_kb.get("process_anomalies", {}).get(anomaly, {})

        if anomaly.startswith("温度超标"):
            eval_result = evaluate_temp_overrun(alloy, temperature, text)
            return {
                "type": "process_anomaly",
                "alloy": alloy,
                "state": state,
                "anomaly_type": anomaly,
                "measured_value": temperature,
                "result": eval_result,
            }

        # 其他工艺异常
        return {
            "type": "process_anomaly",
            "alloy": alloy,
            "state": state,
            "anomaly_type": anomaly,
            "anomaly_data": anomaly_data,
            "context": text,
        }

    elif "固溶" in text or "时效" in text or "热处理" in text or "热处理制度" in text:
        # 热处理参数查询
        if alloy and state:
            result = query_heat_treatment(alloy, state)
            return {
                "type": "parameter_query",
                "alloy": alloy,
                "state": state,
                "result": result,
            }
        elif alloy:
            # 返回所有状态
            params_p = get_params()
            sol = params_p.get("solution_parameters", {}).get(alloy, {})
            aging_all = params_p.get("aging_parameters", {}).get(alloy, {})
            return {
                "type": "parameter_query",
                "alloy": alloy,
                "state": None,
                "available_states": list(aging_all.keys()) if aging_all else [],
                "solution": sol,
                "standard_clause": "HB5480-91 表6、表7",
            }
        else:
            return {
                "type": "parameter_query",
                "alloy": None,
                "error": "请提供合金牌号（如ZL105A）和热处理状态（如T6）",
            }

    elif "力学" in text or "抗拉" in text or "屈服" in text or "伸长" in text:
        # 力学性能查询
        if alloy and state:
            result = query_mechanical_properties(alloy, state)
            return {
                "type": "mechanical_query",
                "alloy": alloy,
                "state": state,
                "result": result,
            }
        else:
            return {
                "type": "mechanical_query",
                "error": "请提供合金牌号和热处理状态",
            }

    elif "取样" in text or "抽样" in text or "检验" in text:
        # 检验规则查询
        sampling = get_sampling()
        # 晶间腐蚀：仅ZL205A T7需要（由diagnose层判断，不在渲染层判断）
        need_ic = (alloy == "ZL205A" and state == "T7")
        return {
            "type": "inspection_query",
            "alloy": alloy,
            "state": state,
            "context": text,
            "sampling": sampling,
            "need_intergranular_corrosion": need_ic,
        }

    else:
        # 元问题检测：在术语匹配之前拦截
        META_PATTERNS = [
            "怎么判定", "如何判断", "如何评定", "判定流程",
            "怎么检验", "如何检验", "标准是什么", "要求是什么",
            "缺陷.*判定", "X射线.*判定", "怎么.*缺陷",
        ]
        for pattern in META_PATTERNS:
            if pattern in text:
                return {
                    "type": "meta_guidance",
                    "context": text,
                    "content": (
                        "要判定缺陷，请提供具体信息：\n\n"
                        "X射线发现的**缺陷类型**、**数量**和**铸件厚度**。\n\n"
                        "示例：\n"
                        "- \"X射线发现1个偏析，厚度15mm\" → 偏析为零容忍，直接拒收\n"
                        "- \"X射线发现3个气孔，厚度8mm\" → 需评级后判定\n"
                        "- \"X射线发现裂纹，厚度10mm\" → 裂纹零容忍，直接拒收"
                    ),
                }

        # 术语查询：在 terminology.yaml 中匹配词条
        terms_data = get_terms()
        terminology = terms_data.get("terminology", {}) if terms_data else {}
        # 检查问题文本是否包含任一术语词条
        matched = {}
        for term_key in terminology:
            if term_key in text:
                matched[term_key] = terminology[term_key]
        if matched:
            return {
                "type": "terminology_query",
                "matched": matched,
                "context": text,
            }
        # 确实无法识别
        return {
            "type": "general",
            "text": text,
            "alloy": alloy,
            "state": state,
            "error": "无法识别问题类型，请描述：缺陷/工艺参数/力学性能/检验要求",
        }

# ============================================================
# CLI 入口（调试用）
# ============================================================

if __name__ == "__main__":
    import json, sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("用法: python diagnose.py <问题文本>")
        print()
        print("示例:")
        print('  python diagnose.py "ZL105A T6固溶温度是多少"')
        print('  python diagnose.py "X射线发现3个气孔，厚度8mm"')
        print('  python diagnose.py "固溶炉温度到545度了"')
        sys.exit(1)

    result = diagnose(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
