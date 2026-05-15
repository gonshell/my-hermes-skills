# AI 硬件 Benchmark 数据来源参考

> **定位说明**：本文件记录 AI 芯片（GPU/NPU）Benchmark 数据核查的经验沉淀，适用于硬件类技术调研报告。
> 当报告主题为非硬件领域（云原生、数据库、前端框架等）时，数据收集方法遵循 SKILL.md「第二阶段：数据收集」的通用方法论，不参考本文件的具体 URL 和数据源。

> 本文件由 `tech-research-doc` skill 维护，记录 AI 硬件（GPU/NPU）Benchmark 数据来源的核查经验。

---

## 一、可信的公开数据源

### 1.1 NVIDIA GPU

| 来源 | URL | 内容 | 可信度 |
|------|-----|------|--------|
| NVIDIA H100 产品页 | https://www.nvidia.com/en-us/data-center/h100/ | 性能宣传数据、NVLink 900 GB/s、"3 TB/s" 带宽 | 高（官方） |
| NVIDIA H100 Datasheet (PDF) | https://resources.nvidia.com/en-us-hopper-architecture/nvidia-tensor-core-gpu-datasheet | SXM5 精确规格：FP16 TC **989 TFLOPS**、HBM3 **3.35 TB/s** | 最高 |
| NVIDIA H100 NVL Product Brief | https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/PB-11773-001_v01.pdf | GPT-3 训练 **4X vs A100**、Megatron 530B 推理 **30X vs A100** | 高 |
| NVIDIA Deep Learning Performance Guide | https://docs.nvidia.com/deeplearning/performance/ | GEMM Arithmetic Intensity 理论、FLOPS:Byte 比值分析 | 高 |
| NVIDIA Nsight 官方文档 | https://developer.nvidia.com/nsight-systems , https://developer.nvidia.com/nsight-compute | Profiling 工具完整文档 | 高 |

> **注意**：官方产品页标注的"3 TB/s"是营销口径，SXM5 实为 **3.35 TB/s**（Datasheet 精确值）。做严肃技术文档时，优先引用 Datasheet。

### 1.2 MLCommons — 全球最具公信力的 AI Benchmark 联盟

| 来源 | URL | 内容 | 可信度 |
|------|-----|------|--------|
| MLCommons 首页 | https://mlcommons.org | 基准测试联盟官方 | 高 [N] |
| MLPerf Inference Datacenter | https://mlcommons.org/benchmarks/inference-datacenter/ | 推理 benchmark 官方结果 | 高 [N] |
| MLPerf Inference v3.1 | https://mlcommons.org/en/inference-datacenter-31/ | 官方发布的 datacenter 推理结果 | 高 [N] |
| MLPerf Training | https://mlcommons.org/benchmarks/training/ | 训练 benchmark 官方结果 | 高 [N] |

> **MLCommons 是国产芯片适配调研的首选中立数据源**：昇腾在其上提交结果极少，这本身就是一个重要结论——在 MLPerf 上无提交的芯片，难以做性能横向比较。

### 1.3 开源推理框架

| 来源 | URL | 内容 | 可信度 |
|------|-----|------|--------|
| vLLM GitHub benchmarks/ | https://github.com/vllm-project/vllm/tree/main/benchmarks | `benchmark_throughput.py`、`benchmark_serving.py` 含实测脚本 | 高（官方代码） |
| vLLM Benchmark 文档 | https://docs.vllm.ai/en/latest/benchmarking/ | 官方 benchmark 工具链文档 | 高 |
| vLLM Performance Dashboard | https://docs.vllm.ai/en/latest/benchmarking/dashboard/ | CI 自动运行的持续集成 benchmark | 高 [N] |
| vLLM Paper (SOSP 2023) | https://www.usenix.org/conference/sosp2023/presentation/yu | PagedAttention 学术论文，实测数据来源 | 最高（学术同行评审） |

> **vLLM 吞吐数据说明**：vLLM GitHub 有 benchmark 脚本，但无官方公开的"H100 单卡吞吐 tok/s"汇总表。需自己跑脚本或引用第三方测评。benchmark_throughput.py 是标准实测工具，可在目标硬件上运行获取精确数字。

### 1.4 分布式训练框架

| 来源 | URL | 内容 | 可信度 |
|------|-----|------|--------|
| DeepSpeed GitHub | https://github.com/microsoft/DeepSpeed | 含昇腾 HCCL 适配代码（非官方维护） | 中 |
| MindSpore 官网 | https://www.mindspore.cn/ | 华为官方分布式训练文档 | 高（官方） |
| HuggingFace Quantization 文档 | https://huggingface.co/docs/transformers/main/en/quantization | INT8/INT4 量化方法论 | 高 |

### 1.5 国产芯片来源

| 来源 | URL | 内容 | 可信度 |
|------|-----|------|--------|
| 昇腾社区 | https://www.hiascend.com/ | 技术文章、MindIE 使用文档 | 中（官方但非 Datasheet） |
| 华为云昇腾文档 | https://support.huaweicloud.com/ | CANN 工具链文档 | 中 |
| 昆仑 SDK 文档 | — | 需登录获取 | 低-中 |

---

## 二、国产芯片数据缺口说明

### 2.1 核心问题

**华为从未发布昇腾 910B 官方 Datasheet**（类似 NVIDIA H100 Datasheet 的完整技术规格文档）。

这意味着以下数据**无官方来源**：

| 数据项 | 业界广泛引用值 | 来源 | 可信度 |
|--------|-------------|------|--------|
| FP16 算力 | ~320 TFLOPS | 昇腾社区技术文章 / 第三方测评 | 中（多方印证） |
| 显存带宽 | ~900 GB/s | 行业技术分析 | 中 |
| HCCS 互联带宽 | ~392-400 GB/s | 开发者论坛讨论 | 低-中 |
| 推理吞吐 | ~600-800 tok/s (LLaMA-7B) | 基于硬件参数估算 | 低-中 |
| 多卡扩展效率 | 8卡 ~85% | 行业测算，无公开 Benchmark | 低 |

### 2.2 应对策略

**核查优先级（按本次验证经验排序）：**

```
优先级 1：官方 Datasheet PDF
  └── nvidia.com/content/dam/en-zz/.../nvidia-tensor-core-gpu-datasheet
  └── 精确规格（FP16 TC 算力、显存带宽精确值）

优先级 2：MLCommons 官方 Benchmark 结果
  └── mlcommons.org/benchmarks/inference-datacenter/
  └── mlcommons.org/benchmarks/training/
  └── 全球最权威 AI 芯片性能数据，独立于厂商

优先级 3：开源框架官方数据
  └── vLLM SOSP 2023 Paper（学术同行评审）
  └── DeepSpeed GitHub（非官方适配，需注明）
  └── vLLM benchmark_throughput.py（自己跑脚本）

优先级 4：厂商官方生态文档
  └── 昇腾社区 hiascend.com
  └── MindSpore 官方文档
  └── 可信度高，但非 Datasheet

优先级 5：行业经验值（[T] / [E]）
  └── 多方印证的技术参数
  └── 需标注"未经独立验证"
```

**快速失败原则（本会话验证）：**

```
1. browser_navigate 直接访问优先级 1-2 的官方来源
   ↓ 失败（404 / 超时 / Bot 检测）
2. 换备选 URL（官网 → GitHub → 技术博客）
   ↓ 失败
3. 快速降级：标注 [T] 或 [E]，不反复换 URL 重试
   ↓
4. 生成「数据缺口报告」，说明已尝试渠道和失败原因
```

> **本会话教训**：花大量时间在不可恢复的 404/超时/Bot 检测拦截上是无意义的。应该快速确认数据不可用后立即切换到"有据可查的降级方案"，而不是反复重试。

### 2.3 数据可信度标注规则

| 标注 | 含义 | 使用场景 |
|------|------|---------|
| `[N]` | 官方发布（Datasheet、MLCommons 官方结果、学术同行评审论文） | 直接引用，标注来源 URL |
| `[T]` | 行业经验值（未经独立验证） | 多方印证的估算，注明"非官方" |
| `[E]` | 基于公开信息的估算 | 仅用于填补空缺，注明推断依据 |

---

## 三、核查检查清单（快速版）

### 每次核查时必查

- [ ] 数据是否来自官方 Datasheet / MLCommons 官方结果
- [ ] 测试条件是否说明（模型、精度、batch_size、序列长度）
- [ ] 国产芯片数据是否标注了 [T] 或 [E]
- [ ] 无法核实的内容是否注明了数据缺口
- [ ] NVIDIA 带宽数据：区分营销口径（"3 TB/s"）vs Datasheet 精确值（3.35 TB/s）

### 本次会话验证过的 URL

| URL | 状态 | 备注 |
|-----|------|------|
| nvidia.com/en-us/data-center/h100/ | ✅ 可访问 | 含 NVLink 900 GB/s、"3 TB/s" 带宽 |
| resources.nvidia.com/...datasheet | ✅ PDF 可访问 | SXM5 FP16 TC 989 TFLOPS |
| mlcommons.org | ✅ 可访问 | MLCommons 首页 |
| mlcommons.org/benchmarks/inference-datacenter/ | ✅ 可访问 | MLPerf Inference 入口 |
| mlcommons.org/en/inference-datacenter-31/ | ✅ 可访问 | MLPerf v3.1 结果页 |
| docs.vllm.ai/en/latest/benchmarking/ | ✅ 可访问 | vLLM 官方 benchmark 文档 |
| docs.vllm.ai/en/latest/benchmarking/dashboard/ | ✅ 可访问 | vLLM Performance Dashboard |
| github.com/vllm-project/vllm/benchmarks | ✅ 可访问 | benchmark_throughput.py 存在 |
| docs.nvidia.com/deeplearning/performance/...matrix-multiplication | ✅ 可访问 | GEMM/Arithmetic Intensity 理论 |
| developer.nvidia.com/blog/nvidia-h100-gpu-benchmarks | ❌ 404 | 该博客文章已被移除 |
| hiascend.com/昇腾产品页 | ❌ 404 | 部分页面不存在 |
| hud.pytorch.org/benchmark/llms | ❌ 页面错误 | PyTorch HUD 不可用 |
| vast.ai/blog/... | ❌ 404 | 特定博客文章不存在 |
| medium.com (LLM 测评文章) | ❌ Bot 检测 | Cloudflare 拦截 |

---

## 四、关键教训

1. **NVIDIA 数据**：优先查 Datasheet PDF，而非产品营销页。营销页数据可能与 Datasheet 有差异（带宽 3 TB/s vs 3.35 TB/s）。

2. **昇腾数据**：无官方 Datasheet，所有参数均为行业引用。核查时快速确认缺口，立即标注 [T]，不反复尝试。

3. **MLCommons 是核心工具**：国产芯片适配调研必访 MLCommons，若芯片在其上无提交记录，则该芯片缺乏国际公信力对标数据，这本身就是重要结论。

4. **vLLM 吞吐数据**：vLLM GitHub 有 benchmark 脚本，但无官方"H100 tok/s 汇总表"。benchmark_throughput.py 是标准实测工具，应告知用户需在目标硬件上自行运行。

5. **多卡扩展效率**：最难获取的数据。NVIDIA 有官方扩展性曲线，昇腾几乎无公开数据。以 [E] 估算处理，并在文档中注明数据来源不可验证。
