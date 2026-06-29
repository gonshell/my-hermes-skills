#!/usr/bin/env python3
"""
trends_ranker.py - 4 板块排序函数

把"文字描述的判断标准"变成可执行代码。
每个维度一个独立函数,纯函数(输入 dict,输出排序 key)。

用法:
    from trends_ranker import rank
    sorted_items = rank(items, "model")

数据字段定义见文件内注释。
"""

from typing import Any, Dict


# =========================================================================
# 共用:厂商量级评分
# =========================================================================
VENDOR_TIER = {
    "head_l1": {
        "月之暗面", "Kimi", "Moonshot", "MoonshotAI",
        "DeepSeek", "deepseek-ai", "深度求索",
        "阿里", "通义", "Qwen", "通义千问",
        "智谱", "Zhipu", "ZhipuAI", "GLM",
        "字节", "豆包", "ByteDance",
        "百度", "文心",
        "腾讯", "混元", "Hunyuan",
        "阶跃", "StepFun",
        "小米", "MiMo", "XiaoMi",
    },
    "head_l2": {
        "MiniMax", "minimax",
        "百川", "Baichuan",
        "商汤", "SenseTime",
        "零一万物", "Yi",
        "面壁", "ModelBest",
        "上海AI实验室", "书生", "InternLM", "InternVL",
        "RWKV",
        "TeleChat", "电信",
        "HuatuoGPT", "华佗",
    },
}


def vendor_score(vendor: str) -> int:
    if not vendor:
        return 0
    v = vendor.strip().lower()
    for tier in VENDOR_TIER["head_l1"]:
        if tier.lower() in v or v in tier.lower():
            return 10
    for tier in VENDOR_TIER["head_l2"]:
        if tier.lower() in v or v in tier.lower():
            return 6
    return 0


# =========================================================================
# 趋势词分类
# =========================================================================
TREND_FOCUS = {
    "agent": 30, "fp4": 28, "reasoning": 25, "moe": 22,
    "long_ctx": 20, "small": 18, "code": 15, "multimodal": 12,
    "video": 10, "flash": 8, "diffusion": 5, "cv": 3, "nlp": 2,
    "agent_runtime": 25, "enterprise": 20, "fintech": 18,
    "voice": 12, "image": 8, "search": 6, "database": 5, "utility": 3,
    "": 0,
}

TREND_STRENGTH = {"rising_fast": 30, "rising": 20, "stable": 5, "": 0}

DATASET_TYPE = {
    "agent_traj": 30, "code_bench": 28, "reasoning_sft": 25,
    "multimodal_sft": 20, "pretrain": 10, "cv_classic": 3, "": 0,
}

PAPER_FOCUS = {
    "new_arch": 30, "scaling": 25, "training": 20, "quant": 18,
    "multimodal": 15, "long_ctx": 12, "world_model": 10, "3d": 8,
    "agent_frame": 6, "agent_app": 4, "fin_app": 2, "": 0,
}


# =========================================================================
# 排序函数
# =========================================================================
def rank_models(item: Dict[str, Any]) -> tuple:
    """模型排序:趋势词(100) > 厂商(10) > 新发 > HOT > 名字"""
    focus = item.get("focus", "")
    return (
        TREND_FOCUS.get(focus, 0) * 100,
        vendor_score(item.get("vendor", "")) * 10,
        1 if item.get("is_new") else 0,
        1 if item.get("hot") else 0,
        item.get("name", ""),
    )


def rank_datasets(item: Dict[str, Any]) -> tuple:
    """数据排序:趋势强度(100) > 任务类型(10) > 名字"""
    return (
        TREND_STRENGTH.get(item.get("trend", ""), 0) * 100,
        DATASET_TYPE.get(item.get("type", ""), 0) * 10,
        item.get("name", ""),
    )


def rank_tools(item: Dict[str, Any]) -> tuple:
    """工具排序:体量(100) > 场景分类(10) > 独家 > HOT > 名字"""
    scale = item.get("scale", 1)
    scale_score = 30 if scale >= 100 else 20 if scale >= 10 else 10 if scale >= 2 else 5
    return (
        scale_score * 100,
        TREND_FOCUS.get(item.get("category", ""), 0) * 10,
        10 if item.get("exclusive") else 0,
        1 if item.get("hot") else 0,
        item.get("name", ""),
    )


def rank_papers(item: Dict[str, Any]) -> tuple:
    """论文排序:HF排名(100) > 方向(10) > 机构 > 名字"""
    rank = item.get("hf_rank", 999)
    rank_score = max(0, 1000 - rank * 10)
    return (
        rank_score * 100,
        PAPER_FOCUS.get(item.get("focus", ""), 0) * 10,
        vendor_score(item.get("org", "")) * 5,
        item.get("name", ""),
    )


RANKERS = {"model": rank_models, "data": rank_datasets, "tool": rank_tools, "paper": rank_papers}


def rank(items: list, dimension: str, reverse: bool = True) -> list:
    """统一排序入口"""
    if dimension not in RANKERS:
        raise ValueError(f"unknown dimension: {dimension}")
    return sorted(items, key=RANKERS[dimension], reverse=reverse)


if __name__ == "__main__":
    # 快速验证
    models = [
        {"name": "Kimi-K2.7-Code", "vendor": "月之暗面", "focus": "code", "is_new": True, "hot": True},
        {"name": "MiMo-FP4", "vendor": "小米", "focus": "fp4", "is_new": True},
        {"name": "VibeThinker-3B", "vendor": "—", "focus": "small", "is_new": True},
    ]
    print("模型排序:")
    for i, m in enumerate(rank(models, "model"), 1):
        print(f"  {i}. {m['name']} (focus={m['focus']})")
