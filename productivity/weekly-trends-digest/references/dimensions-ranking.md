# Per-Dimension Ranking Rules

Full derivation of the weight + tiebreaker rules used in `scripts/trends_ranker.py`. Read this when you want to **change the weights**, **add a new dimension**, or **understand why the current defaults rank the way they do**.

## Why fixed order: 模型 → 数据 → 工具 → 论文

This is the **signal-strength ordering** for catching trends, not the learning-value ordering:

| Rank | Dimension | Why here | Evidence speed |
|------|-----------|----------|----------------|
| 1 | 模型 | Strongest, fastest-changing signal. A new model lands → everyone sees same day | Days (one push = news) |
| 2 | 数据 | Lags behind but points to training paradigm shifts | Weeks (new dataset → training → new model) |
| 3 | 工具 | Protocol layer changes; volume high but per-item value low | Weeks to months |
| 4 | 论文 | Academic is slowest, highest noise. Most papers are micro-increments | Months |

**Principle**: closer to "deployed thing" goes first. Closer to "idea" goes last.

## Per-dimension rules

### 模型 (model)

Primary key (weight 100): **trend focus**. From highest to lowest in the current 2026 landscape:

```
agent: 30       (Agent / GUI 操作 — current top trend)
fp4: 28         (FP4 量化 — 2026 new direction)
reasoning: 25   (CoT / o1 风格推理)
moe: 22         (MoE 架构变体 — MoE-DSA etc.)
long_ctx: 20    (128K+ 长上下文)
small: 18       (小尺寸本地化 ≤3B)
code: 15        (代码 SOTA)
multimodal: 12  (多模态)
video: 10       (视频生成)
flash: 8        (Flash 推理)
diffusion: 5    (扩散模型
cv: 3           (通用 CV 兜底)
nlp: 2          (通用 NLP 兜底)
```

Tiebreaker (weight 10): **vendor tier**.

```
L1 head  (defines trends): 月之暗面, DeepSeek, 阿里/Qwen, 智谱/GLM, 字节, 百度, 腾讯, 阶跃, 小米
L2 mid   (followers with own capability): MiniMax, 百川, 商汤, 零一万物, 面壁, 上海AI实验室, 电信/TeleChat
tail     (use content quality instead)
```

Then `is_new` (1/0), then `hot` flag, then alphabetical.

**Why trend focus × 100, vendor × 10**: a 10× gap forces the ranker to prefer "fp4 is heating up" over "head vendor did something generic" — which matches the goal of catching emerging trends.

### 数据 (data)

Primary key (weight 100): **trend strength**. The arrows reflect how actively the dataset is being added to / used:

```
rising_fast: 30   (↑↑ — newest, most scarce)
rising:      20   (↑ — active growth)
stable:       5   (→ — established, predictable)
```

Tiebreaker (weight 10): **task type importance**. 2026 priorities:

```
agent_traj: 30       (Agent 训练轨迹 — most scarce, RL data)
code_bench: 28       (SWE-bench 类)
reasoning_sft: 25    (推理 SFT)
multimodal_sft: 20   (多模态 SFT)
pretrain: 10         (预训练)
cv_classic: 3        (兜底)
```

Then alphabetical.

**Why trend × 100, task × 10**: a rising-fast agent trajectory dataset beats a stable pretraining one even if pretrain is "more important" abstractly. We're catching signals, not making a curriculum.

### 工具 (tool)

Primary key (weight 100): **scale** (how many services dropped in one batch). Bucket:

```
≥100: 30    (one-shot mega-drops —钉钉 × 200)
≥10:  20
≥2:   10
1:     5    (single normal release)
```

Tiebreaker (weight 10): **category importance**:

```
agent_runtime: 25
enterprise:    20   (企业 OA / 钉钉 / 飞书)
fintech:       18   (金融 / 支付)
video:         15
voice:         12
image:          8
search:         6
database:       5
utility:        3
```

Then `exclusive` flag (独家首发 vs ordinary list), then `hot`, then alphabetical.

**Why scale first**: one 200-shot drop (钉钉) is a *trend signal* (industry pivot), while 200 single releases over a quarter is *growth*. The former is news, the latter is noise.

### 论文 (paper)

Primary key (weight 100): **HF Trending rank**. Score = `1000 - rank*10`, so:

```
rank 1: 990
rank 2: 980
...
rank 0: -∞  (treated as 0, fall through to focus)
```

**Important**: when rank is unknown (0 / None), don't penalize — fall through to focus score. See `scripts/trends_ranker.py` for the fallback handling.

Tiebreaker (weight 10): **paper focus**:

```
new_arch:    30   (新架构 MoE-DSA 等)
scaling:     25   (规模定律)
training:    20   (训练方法 RLHF/DPO/GRPO)
quant:       18   (FP4/INT4)
multimodal:  15   (多模态架构)
long_ctx:    12
world_model: 10
3d:           8
agent_frame:  6   (Agent 框架)
agent_app:    4   (Agent 应用 — 股票交易等)
fin_app:      2   (金融应用)
```

Then `org tier` (vendor_score × 5), then alphabetical.

**Why HF rank first**: HF's curation is already a strong signal. We don't need to second-guess it.

## How to change the weights

When you edit weights, edit **both**:
1. The constant dictionaries in `scripts/trends_ranker.py`
2. This file (so the next session knows why the numbers are what they are)

If the user says "趋势 doesn't catch up anymore", check whether:
- The focus weights are still accurate (e.g. fp4 might be cooling off; bump it down)
- The vendor L1 list is still right (new players enter every quarter)
- The data trend strength scores still reflect what's actually rare

## What this is NOT

- Not a curated editorial ranking — it's a deterministic, reproducible function
- Not a replacement for reading the actual model paper — it sorts, it doesn't evaluate
- Not a scoring model that learns — no ML, no historical weights. The ranking is fixed and explicit. If you want it to learn, that's a different (much bigger) skill