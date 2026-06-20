# bilibili-ai-trending — 2026-06-19 实测增量

> 本文补充 `bilibili-ai-trending-pitfalls-2026-06-16.md`。

## 1. execute_code 中 `json_parse` 不是全局内置

hermes_tools 的 `json_parse()` 在 `execute_code` 脚本中 **不能直接调用**（`NameError: name 'json_parse' is not defined`）。它只在 `from hermes_tools import ...` 后作为模块函数可用，但文档说"no import needed — built into hermes_tools"容易误导。

**两种可用方案**：

```python
# 方案 A：标准库（推荐，无需 import 额外模块）
import json
data = json.loads(raw_string, strict=False)  # strict=False 允许控制字符

# 方案 B：subprocess 跑独立 Python 脚本（适合大文件）
# 写脚本到文件，用 subprocess.run(['python3', 'script.py']) 执行
```

**踩坑记录**：2026-06-19 session 连续 3 次 `NameError`，根因是把 `json_parse` 当作 execute_code 全局函数使用。最终改用 `subprocess.run(['python3', '-c', '...'])` 方案绕过。

## 2. Word-boundary 正则过滤 AI 关键词是必须的

Bilibili 热门/排行数据中，简单子串匹配 `if 'AI' in text` 会产生大量假阳性：

| 假阳性标题 | 误匹配原因 |
|-----------|-----------|
| "假如所有人被迫看着死亡回归" | desc 含 "again"（含 "ai" 子串） |
| "《原神》前瞻特别节目" | desc 含 "maintain"（含 "ai" 子串） |
| "真人歌单 · 兜风神曲" | desc 含 "captain"（含 "ai" 子串） |
| "莉爱牛逼" | 标题含 "ai" 子串 |

**正确做法**：对英文缩写关键词必须用 `\b` word-boundary 正则：

```python
import re

# ✅ 正确：word-boundary 匹配
if re.search(r'\bAI\b', text, re.IGNORECASE):
    return True

# ❌ 错误：子串匹配
if 'AI' in text:  # 会匹配 "maintain", "captain", "again" 等
    return True
```

**完整模式分类**：

| 类型 | 匹配方式 | 示例 |
|------|---------|------|
| 英文缩写 | `\b` word-boundary + IGNORECASE | `\bAI\b`, `\bGPT\b`, `\bLLM\b` |
| 英文产品名 | `\b` word-boundary | `\bClaude\b`, `\bDeepSeek\b`, `\bKimi\b` |
| 中文术语 | 精确子串 | `人工智能`, `大模型`, `机器学习` |
| 复合词 | 中文前缀子串 | `AI编程`, `AI画图`, `AI工具` |

**实现模板**：

```python
ai_patterns = [
    # 英文 — word-boundary
    r'\bAI\b', r'\bAIGC\b', r'\bAGI\b', r'\bLLM\b',
    r'\bChatGPT\b', r'\bGPT',  # GPT 前缀匹配 GPT-4/GPT4
    r'\bDeepSeek\b', r'\bClaude\b', r'\bGemini\b',
    r'\bKimi\b', r'\bQwen\b', r'\bLlama\b', r'\bMistral\b',
    r'\bCursor\b', r'\bAnthropic\b', r'\bGrok\b',
    r'\bLoRA\b', r'\bRAG\b', r'\bMCP\b', r'\bCopilot\b',
    r'\bMidjourney\b', r'\bManus\b', r'\bKling\b',
    r'\bNVIDIA\b', r'\bGPU\b',
    # 中文 — 精确子串
    '人工智能', '大模型', '机器学习', '神经网络', '深度学习', '智能体',
    '文生图', '文生视频', '生成式', 'AIGC',
    '通义', '智谱', '豆包', '英伟达',
    'AI编程', 'AI画图', 'AI视频', 'AI绘画', 'AI工具', 'AI助手',
    '多模态', '视觉模型', '语言模型', '算力', '即梦', '可灵',
]

def is_ai_related(title, desc='', tname='', tags=''):
    search_text = f'{title} {desc} {tname} {tags}'
    for pat in ai_patterns:
        if pat.startswith(r'\b'):
            if re.search(pat, search_text, re.IGNORECASE):
                return True
        else:
            if pat in search_text:
                return True
    return False
```

## 3. Search API 中文关键词空格编码

`/x/web-interface/search/type?keyword=AI 人工智能` 含空格的查询返回空响应。

**正确做法**：用 `urllib.parse.quote()` 编码后拼接 URL：

```python
import urllib.parse
keyword = urllib.parse.quote('AI 人工智能')
url = f'https://api.bilibili.com/x/web-interface/search/type?keyword={keyword}&search_type=video&order=click&page=1'
```

**实测**：15 个单关键词查询全部返回 20 条结果；含空格的组合查询（"AI 人工智能"、"大模型 ChatGPT"）全部返回空。优先用单关键词多次请求。

## 4. popular API + ranking API 的 AI 内容占比极低

2026-06-19 实测：popular API 3 页 150 条 + ranking API 100 条 = 206 条去重后，AI 关键词过滤仅命中 **1 条**（"AI长出来的车，到底长什么样？"）。

**结论**：popular + ranking API 不能作为 AI 内容的唯一数据源，**必须搭配 search API**。search API 是精准获取 AI 内容的唯一可靠方式。

**三源合并策略**：
1. search API（15 个关键词 × 20 条）→ 主力，AI 命中率 ~90%
2. popular API（3-5 页）→ 补充，AI 命中率 ~5%
3. ranking API（100 条）→ 补充，AI 命中率 ~1%

## 5. DocxXML 格式 vs 自定义根节点

cron job prompt 经常指定 `<BilibiliAITrending>` 等自定义根节点，但 lark-cli 最佳实践是 `<docx><title>...</title><body>...</body></docx>`。

**2026-06-19 实测**：使用 `<?xml version="1.0"?>` + `<BilibiliAITrending>` 根节点写入飞书，lark-cli 返回 `ok: true` + `result: "success"`。两个 `degrade_code=4007` warning 仅针对非 DocxXML 标签，内部 h1/h2/ol/li/a 全部正常渲染。

**实践建议**：如果 cron prompt 明确指定了根节点格式（如 `<BilibiliAITrending>`），**照做即可**——功能正常，仅多两个 warning。不值得花时间说服用户改格式。
