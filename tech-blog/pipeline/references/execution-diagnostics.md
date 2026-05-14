# 执行策略诊断记录

## 问题：delegate_task写长文连续超时

**日期**：2026-05-14
**模型**：glm-5.1 (智谱/zai)
**配置**：`child_timeout_seconds: 600`

### 症状

```
尝试1: E3a初稿整体写（delegate） → 600秒超时（7次API调用）
尝试2: 拆成ch1-2 + ch3-5并行delegate → ch1-2超时(6次API调用), ch3-5 HTTP 429限流
尝试3: 只写大纲（小任务delegate）→ ✅ 成功（145秒）
尝试4: 再拆分写ch1-2（中等任务delegate）→ 600秒超时（6次API调用）
```

### 根因分析

两个问题叠加：

1. **智谱API限流（HTTP 429）**：delegate子Agent与主Agent共享同一个API配额。并发请求时触发限流，错误信息"该模型当前访问量过大，请您稍后再试"。这不是Hermes内部问题，是外部API的速率限制。

2. **delegate 600秒硬限制**：写5000+字中文技术博客需要读取多个文件（解析素材→读大纲→构思→写作→输出）。glm-5.1的输出速度约3000 token/分钟，加上限流重试，600秒内无法完成。

3. **无降级策略**：delegate_task要么成功要么超时，没有"部分完成"机制。超时后所有已生成内容丢失。

### 规律

- **小任务（<200秒预期）delegate成功率高**：材料解析、大纲设计、审查反馈
- **大任务（>300秒预期）delegate成功率低**：长文写作、多文件整合
- **限流期间重试会加剧问题**：应等待1-2分钟或切换到主session

### 解决方案：A+B混合策略

- **方案A**：主session直接用write_file写长文（阶段4、阶段7）
- **方案B**：小粒度delegate做短任务（阶段1/2/3/5/6/8）

### 效果对比

| 策略 | 成功率 | 平均耗时 |
|------|--------|---------|
| 大任务delegate（旧） | 0/4（全超时/限流） | 600秒超时 |
| A+B混合（新） | 4/4 | 主session写作~2分钟/篇 |

### 关键配置参考

```yaml
# ~/.hermes/config.yaml 相关配置
model:
  default: glm-5.1
  provider: zai
delegation:
  child_timeout_seconds: 600
  max_iterations: 50
  max_concurrent_children: 3
```

### 换模型时的注意事项

如果delegation配置了独立的模型/Provider（`delegation.model`/`delegation.provider`），限流问题可能缓解——子Agent使用不同的API配额。但600秒超时仍然是硬限制，长文写作仍建议主session执行。
