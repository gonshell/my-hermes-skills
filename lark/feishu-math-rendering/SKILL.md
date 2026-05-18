---
name: feishu-math-rendering
version: 1.0.0
description: "飞书文档 LaTeX 公式渲染规范：\\text{} 不支持问题、检测方法、修复步骤。涉及在飞书文档中写入数学公式时使用本 skill。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# feishu-math-rendering

飞书文档的 LaTeX 渲染基于 KaTeX 子集，存在已知限制。

## 核心规则

### ✅ 支持的写法
- 汉字直接写在公式内：`$E = \{x \mid x 是等腰三角形\}$`
- 纯 LaTeX 符号：`$\sqrt{ab} \leq \frac{a+b}{2}$`
- Unicode 符号在公式内：`$180°$`, `$a \geq b$`

### ❌ 不支持的写法
- **`\text{}`**：不支持 amsmath 的 `\text{}`、`\mbox{}`、`\mathrm{}`
  - `$\pi \text{ 弧度} = 180°$` → 显示为 `$\pi \text{ 弧度} = 180°$`
  - `$\text{或}$` → 显示为 `$\text{或}$`
- **后果**：未支持的命令被原样显示，破坏公式可读性

### ✅ 正确写法
```latex
% 错误
$\pi \text{ 弧度} = 180°$

% 正确
$\pi 弧度 = 180°$
```

## 修复已有文档

### 检测
```python
import re, subprocess

# fetch 文档内容
r = subprocess.run(['lark-cli', 'docs', '+fetch', '--api-version', 'v2', '--doc', token], capture_output=True, text=True)
content = json.loads(r.stdout)['data']['document']['content']

# 查找问题模式
text_issues = re.findall(r'\\text\{[^}]+\}', content)
space_chinese = re.findall(r'\\ [\u4e00-\u9fff]', content)  # 如 \ 弧度
```

### 替换
```python
# 直接替换
content = content.replace(r'\text{ 弧度}', ' 弧度')
content = content.replace(r'\text{或}', '或')
content = content.replace(r'\text{ 个 }', ' 个 ')
content = content.replace(r'n \ 个  a', 'n 个 a')

# 清理残留的 \ 汉字 模式
content = content.replace(r'\ 弧度', '弧度')
content = content.replace(r'\ 个', '个')
content = content.replace(r'\ 或', '或')

# 验证无残留
assert '\\text{' not in content
assert not re.search(r'\\ [\u4e00-\u9fff]', content)
```

### 写回
```bash
# 保存到 CWD 相对路径
with open('./fixed_content.xml', 'w') as f:
    f.write(content)

# overwrite（需要 --doc-format xml）
lark-cli docs +update \
  --api-version v2 \
  --doc "TOKEN" \
  --command overwrite \
  --content @./fixed_content.xml \
  --doc-format xml
```

## 编写新内容时

在编写包含中文说明的数学公式时，**直接写汉字**，不要用 `\text{}`：

```latex
% 错误
$n \text{ 个 } a$

% 正确
$n 个 a$
```

## 相关陷阱

- `overwrite` 命令必须同时传 `--doc-format xml`，否则 `<title>` 会被转义为 `&lt;title&gt;`
- 使用 `--content @file` 时，路径必须是 CWD 相对路径（禁止绝对路径）
- 替换 `\text{...}` 后可能残留 `\ ` + 汉字（如 `\ 弧度`），需二次清理