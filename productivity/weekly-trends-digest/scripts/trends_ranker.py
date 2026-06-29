"""
魔搭社区 · 10 分钟趋势速览 — 排序规则库

四个维度的排序函数,把"文字描述"变成可执行代码。

设计原则:
- 纯函数:输入是 item dict,输出是排序 key(降序)
- 单一职责:每个维度一个独立函数,可单独测试
- 可解释:每个函数顶部注释说明排序逻辑
- 可扩展:新增字段或调整权重,只改一处

数据来源(每个 item 是 dict,字段定义见下):
- 模型(model):    name, vendor, tag, focus, is_new, hot
- 数据(data):     name, type, trend
- 工具(tool):     name, provider, category, scale, exclusive
- 论文(paper):    name, org, focus, hf_rank

用法:
    from trends_ranker import rank_models, rank_datasets, rank_tools, rank_papers

    items = [
        {"name": "Kimi-K2.7-Code", "vendor": "月之暗面", "tag": "代码 SOTA", "focus": "code"},
        {"name": "VibeThinker-3B", "vendor": "—", "tag": "小尺寸推理", "focus": "small"},
    ]
    sorted_items = sorted(items, key=rank_models, reverse=True)
"""

from typing import Any, Dict


# =========================================================================
# 共用:厂商量级评分(头部 / 腰部 / 长尾)
# =========================================================================
# 头部厂商:能定义趋势,发布即关注
# 腰部厂商:跟进趋势,发布看质量
# 长尾/未知:内容本身比厂商重要
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
    """
    厂商量级评分:头部 L1=10, 头部 L2=6, 其他=0

    用法:在"同趋势强度"下,头部厂商的模型优先
    """
    if not vendor:
        return 0
    v = vendor.strip()
    for tier in VENDOR_TIER["head_l1"]:
        if tier.lower() in v.lower() or v.lower() in tier.lower():
            return 10
    for tier in VENDOR_TIER["head_l2"]:
        if tier.lower() in v.lower() or v.lower() in tier.lower():
            return 6
    return 0


# =========================================================================
# 共用:趋势词分类(用于"模型 focus"和"工具 category"等的优先级)
# =========================================================================
# 高优先级:2026 当下最热的趋势(Agent / FP4 量化 / 长上下文 / 多模态)
# 中优先级:稳定赛道(代码 / 推理 / 多模态 SFT)
# 低优先级:成熟领域(分类 / ASR / OCR)
TREND_FOCUS = {
    # 模型 focus
    "agent":     30,   # Agent / GUI 操作
    "fp4":       28,   # FP4 量化(2026 新方向)
    "reasoning": 25,   # 推理(CoT / o1 风格)
    "moe":       22,   # MoE 架构变体(MoE-DSA 等)
    "long_ctx":  20,   # 128K+ 长上下文
    "small":     18,   # 小尺寸本地化(≤3B)
    "code":      15,   # 代码 SOTA
    "multimodal":12,   # 多模态
    "video":     10,   # 视频生成
    "flash":      8,   # 推理加速(Flash 类)
    "diffusion":  5,   # 扩散模型
    "cv":         3,   # 通用 CV 兜底
    "nlp":        2,   # 通用 NLP 兜底
    "":           0,
    # 工具 category
    "agent_runtime": 25,
    "enterprise":    20,   # 企业 OA / 钉钉
    "fintech":       18,   # 金融 / 支付
    "video":         15,
    "voice":         12,
    "image":          8,
    "search":         6,
    "database":       5,
    "utility":        3,
}


# =========================================================================
# 模型排序
# =========================================================================
# 排序标准(从重到轻):
#   1. 趋势代表性(agent / fp4 / reasoning) > 通用(代码 / 多模态) > 兜底
#   2. 厂商量级(头部 L1 > L2 > 长尾) — 同趋势强度下生效
#   3. 是否本周新发 + HOT 标签
#   4. 字母顺序兜底
def rank_models(item: Dict[str, Any]) -> tuple:
    """
    模型排序 key(降序)

    item 字段:
        name:    str  — 模型名
        vendor:  str  — 厂商
        tag:     str  — 标签(如 "代码 SOTA", "FP4 量化")
        focus:   str  — 趋势词键(见 TREND_FOCUS),用于直接打分
        is_new:  bool — 是否本周新发
        hot:     bool — 是否 HOT 标记
    """
    focus = item.get("focus", "")
    return (
        # 1. 趋势代表性 (权重 100)
        TREND_FOCUS.get(focus, 0) * 100,
        # 2. 厂商量级 (权重 10)
        vendor_score(item.get("vendor", "")) * 10,
        # 3. 是否本周新发 (1=新, 0=旧)
        1 if item.get("is_new") else 0,
        # 4. HOT 标记
        1 if item.get("hot") else 0,
        # 5. 字母顺序(兜底)
        item.get("name", ""),
    )


# =========================================================================
# 数据排序
# =========================================================================
# 排序标准:
#   1. 趋势强度(↑↑ > ↑ > →) — 最重要
#   2. 任务类型重要性(Agent > 推理 > 多模态 > 预训练)
#   3. 字母顺序兜底
TREND_STRENGTH = {
    "rising_fast": 30,   # ↑↑  双箭头,最稀缺
    "rising":      20,   # ↑
    "stable":       5,   # →
    "":             0,
}

DATASET_TYPE = {
    # 高优先级:2026 训练范式核心
    "agent_traj":    30,   # Agent 训练轨迹
    "code_bench":    28,   # SWE-bench 类
    "reasoning_sft": 25,   # 推理 SFT
    "multimodal_sft":20,   # 多模态 SFT
    "pretrain":      10,   # 预训练
    "cv_classic":     3,   # 兜底
    "":               0,
}


def rank_datasets(item: Dict[str, Any]) -> tuple:
    """
    数据集排序 key(降序)

    item 字段:
        name:  str
        type:  str  — 类型键(见 DATASET_TYPE)
        trend: str  — 趋势强度键(见 TREND_STRENGTH)
    """
    return (
        # 1. 趋势强度 × 100
        TREND_STRENGTH.get(item.get("trend", ""), 0) * 100,
        # 2. 任务类型 × 10
        DATASET_TYPE.get(item.get("type", ""), 0) * 10,
        # 3. 字母顺序
        item.get("name", ""),
    )


# =========================================================================
# 工具排序
# =========================================================================
# 排序标准:
#   1. 体量(一次发布多少个,大单 > 零散)
#   2. 场景分类重要性
#   3. 是否独家(独家首发优先)
#   4. 字母顺序
def rank_tools(item: Dict[str, Any]) -> tuple:
    """
    工具排序 key(降序)

    item 字段:
        name:      str
        provider:  str  — 提供方
        category:  str  — 类别键(见 TREND_FOCUS 的工具部分)
        scale:     int  — 体量(如钉钉 200 个)
        exclusive: bool — 是否独家首发
    """
    # 体量打分(对数,避免钉钉 200 远超别人)
    scale = item.get("scale", 1)
    if scale >= 100:
        scale_score = 30
    elif scale >= 10:
        scale_score = 20
    elif scale >= 2:
        scale_score = 10
    else:
        scale_score = 5

    return (
        # 1. 体量 × 100
        scale_score * 100,
        # 2. 场景分类 × 10
        TREND_FOCUS.get(item.get("category", ""), 0) * 10,
        # 3. 独家 (10)
        10 if item.get("exclusive") else 0,
        # 4. HOT 标记
        1 if item.get("hot") else 0,
        # 5. 字母顺序
        item.get("name", ""),
    )


# =========================================================================
# 论文排序
# =========================================================================
# 排序标准:
#   1. HF 排名(数值越小越好,所以用 1000 - rank)
#   2. 是否反映"新架构/新方向"(基础研究 > 应用)
#   3. 机构量级
#   4. 字母顺序
PAPER_FOCUS = {
    # 基础研究(高优)
    "new_arch":    30,   # 新架构(MoE-DSA 等)
    "scaling":     25,   # 规模定律
    "training":    20,   # 训练方法(RLHF/DPO/GRPO)
    "quant":       18,   # 量化(FP4/INT4)
    "multimodal":  15,   # 多模态架构
    "long_ctx":    12,   # 长上下文技术
    "world_model": 10,   # 世界模型
    "3d":           8,
    "agent_frame":  6,   # Agent 框架
    # 应用层(低优)
    "agent_app":    4,   # Agent 应用(股票交易等)
    "fin_app":      2,
    "":             0,
}


def rank_papers(item: Dict[str, Any]) -> tuple:
    """
    论文排序 key(降序)

    item 字段:
        name:     str
        org:      str  — 机构
        focus:    str  — 关键词键(见 PAPER_FOCUS)
        hf_rank:  int  — HF Trending 排名(1 = #1)
    """
    # HF 排名(数值越大越靠前)
    rank = item.get("hf_rank", 999)
    rank_score = max(0, 1000 - rank * 10)  # #1 = 990, #2 = 980, ...

    return (
        # 1. HF 排名分 × 100
        rank_score * 100,
        # 2. 论文方向 × 10
        PAPER_FOCUS.get(item.get("focus", ""), 0) * 10,
        # 3. 机构量级
        vendor_score(item.get("org", "")) * 5,
        # 4. 字母顺序
        item.get("name", ""),
    )


# =========================================================================
# 统一接口
# =========================================================================
RANKERS = {
    "model": rank_models,
    "data":  rank_datasets,
    "tool":  rank_tools,
    "paper": rank_papers,
}


def rank(items: list, dimension: str, reverse: bool = True) -> list:
    """
    统一排序入口

    Args:
        items:     item dict 列表
        dimension: "model" | "data" | "tool" | "paper"
        reverse:   True=降序(分数高的在前),默认

    Returns:
        排序后的新列表
    """
    if dimension not in RANKERS:
        raise ValueError(f"unknown dimension: {dimension}, must be one of {list(RANKERS)}")
    return sorted(items, key=RANKERS[dimension], reverse=reverse)


# =========================================================================
# 演示 + 单元测试
# =========================================================================
if __name__ == "__main__":
    models = [
        {"name": "Kimi-K2.7-Code",          "vendor": "月之暗面",   "tag": "代码 SOTA",   "focus": "code",       "is_new": True,  "hot": True},
        {"name": "MiMo-V2.5-Pro-FP4-DFlash","vendor": "小米",       "tag": "FP4 量化",    "focus": "fp4",        "is_new": True,  "hot": False},
        {"name": "VibeThinker-3B",           "vendor": "—",          "tag": "小尺寸推理",  "focus": "small",      "is_new": True,  "hot": False},
        {"name": "Step-3.7-Flash",           "vendor": "阶跃",       "tag": "Flash 推理",  "focus": "flash",      "is_new": True,  "hot": False},
        {"name": "Rio-3.5-Open-397B",        "vendor": "—",          "tag": "大尺寸开源",  "focus": "nlp",        "is_new": True,  "hot": False},
        {"name": "Nex-N2-Pro",               "vendor": "—",          "tag": "通用 Pro",    "focus": "nlp",        "is_new": True,  "hot": False},
        {"name": "diffusiongemma-26B-A4B-it","vendor": "Google",     "tag": "扩散+指令",  "focus": "diffusion",  "is_new": True,  "hot": False},
    ]

    print("=" * 60)
    print("模型排序结果")
    print("=" * 60)
    for i, m in enumerate(rank(models, "model"), 1):
        print(f"{i}. {m['name']:30s}  focus={m['focus']:10s}  vendor={m['vendor']}")

    datasets = [
        {"name": "SWE-agent-trajectories",     "type": "agent_traj",    "trend": "rising_fast"},
        {"name": "SWE-bench-extra",            "type": "code_bench",    "trend": "rising_fast"},
        {"name": "fineweb-c",                  "type": "pretrain",      "trend": "stable"},
        {"name": "LLaVA-CoT-o1-Instruct",      "type": "multimodal_sft","trend": "rising"},
        {"name": "OpenO1-SFT",                 "type": "reasoning_sft", "trend": "rising"},
        {"name": "Infinity-MM",                "type": "multimodal_sft","trend": "stable"},
    ]
    print("\n" + "=" * 60)
    print("数据排序结果")
    print("=" * 60)
    for i, d in enumerate(rank(datasets, "data"), 1):
        print(f"{i}. {d['name']:30s}  type={d['type']:15s}  trend={d['trend']}")

    tools = [
        {"name": "钉钉办公套件",        "provider": "钉钉",   "category": "enterprise", "scale": 200, "exclusive": True},
        {"name": "MiniMax 视频生成 MCP","provider": "MiniMax","category": "video",      "scale": 1,   "exclusive": True, "hot": True},
        {"name": "MiniMax 语音 MCP",     "provider": "MiniMax","category": "voice",      "scale": 1,   "exclusive": True},
        {"name": "支付宝支付 MCP",       "provider": "支付宝", "category": "fintech",    "scale": 1,   "exclusive": False},
        {"name": "Skills 目录",          "provider": "社区",   "category": "utility",    "scale": 5,   "exclusive": False},
    ]
    print("\n" + "=" * 60)
    print("工具排序结果")
    print("=" * 60)
    for i, t in enumerate(rank(tools, "tool"), 1):
        print(f"{i}. {t['name']:20s}  scale={t['scale']:4d}  cat={t['category']:10s}  excl={t['exclusive']}")

    papers = [
        {"name": "Gemma 4 Family",            "org": "Google",         "focus": "scaling",     "hf_rank": 1},
        {"name": "MoE-DSA 架构",              "org": "DeepSeek",       "focus": "new_arch",    "hf_rank": 0},
        {"name": "GLM-5.1 配套",              "org": "智谱",           "focus": "new_arch",    "hf_rank": 0},
        {"name": "HY-OmniWeaving",            "org": "腾讯",           "focus": "multimodal",  "hf_rank": 0},
        {"name": "Latent spatial memory",     "org": "—",              "focus": "world_model", "hf_rank": 0},
        {"name": "多 Agent stock trading",    "org": "—",              "focus": "agent_app",   "hf_rank": 0},
    ]
    print("\n" + "=" * 60)
    print("论文排序结果")
    print("=" * 60)
    for i, p in enumerate(rank(papers, "paper"), 1):
        print(f"{i}. {p['name']:30s}  rank={p.get('hf_rank', 999):3d}  focus={p['focus']:12s}  org={p['org']}")