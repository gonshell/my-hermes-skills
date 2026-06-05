# 飞书文档结构规范（2026-05-30 方案A：档期主体结构）

## 目录生成规则

飞书文档的**目录功能**依赖标准 HTML 标题标签（`<h1>`、`<h2>`）自动生成目录层级。

- ✅ `<h1>` → 飞书目录一级标题（对应目录中的大章节）
- ✅ `<h2>` → 飞书目录二级标题（对应目录中的子章节）
- ❌ 自定义 XML 标签（`<section>`、`<item>`、`<root>` 等）→ 飞书解析为纯文本，**目录空白**

---

## 方案A：档期主体结构（推荐，用于单文档多档期）

**h1 格式**：`{任务名} · {日期} · {档期}`

```
<h1>每日AI热门视频推送 · 2026-05-30 · 早间档</h1>
  <h2>最热门长视频 TOP 10</h2>
  <p>本周上传，播放量+互动率综合评分排序</p>
  <ol><li>视频1</li>...</ol>
  <h2>最热门短视频 TOP 5</h2>
  <ol><li>视频1</li>...</ol>
  <h2>当日新发热门视频 TOP 10</h2>
  <ol><li>视频1</li>...</ol>

<h1>每日AI热门视频推送 · 2026-05-30 · 晚间档</h1>
  <h2>最热门长视频 TOP 10</h2>
  ...
```

**适用场景**：同一文档中同一任务早晚两档并存，或多任务写入同一文档时。

### YouTube 文档结构（OoxcdJ72worwMHxwK73ctbdhn0b）

| 档期 | h1 格式 | cron 任务 | 写入模式 |
|------|---------|-----------|---------|
| 早间档 | `每日AI热门视频推送 · {日期} · 早间档` | job fa294bf7d232（06:00） | overwrite |
| 晚间档 | `每日AI热门视频推送 · {日期} · 晚间档` | job d470b5d9b593（20:00） | overwrite |

**⚠️ 碰撞问题**：两个 YouTube 任务都使用 `overwrite`，同时触发会互相覆盖。

**解法（推荐）**：早间档任务每次 `overwrite` 写入**完整双档期结构**（早间档 + 晚间档占位）。晚间档任务也 `overwrite` 完整双档期结构。两次写入内容相同，正常定时运行时（早06:00、晚20:00）不会碰撞。测试场景避免同时触发。

### Bilibili 文档结构（MjT6dT3abopHBpxkwPCcauGWn6e）

| 档期 | h1 格式 | cron 任务 | 写入模式 |
|------|---------|-----------|---------|
| AI热门档 | `每日Bilibili AI热门推送 · {日期} · 晚间档` | job 1f4c7fb989aa（21:00） | append |
| 全站热门档 | `每日Bilibili全站热门推送 · {日期} · 晚间档` | job 0e9f3cb36fe6（22:00） | overwrite |

**注意**：AI热门（append）和全站热门（overwrite）写入不同 h1，append 追加在文档末尾，两者可共存于同一文档。

---

## 方案B：内容类型主体结构（备选）

**h1 格式**：`{内容分类名}`

```
<h1>最热门长视频 TOP 10</h1>
  <h2>2026-05-30 晚间档</h2>
  <ol><li>...</li></ol>
  <h2>2026-05-30 早间档</h2>
  <ol><li>...</li></ol>
```

适用于：同一内容分类下多天、多档期数据需要横向对比。

---

## XML 模板

### YouTube 模板（方案A 双档期结构）

```xml
<docx><title>YouTube AI热门视频 · 晚间档</title><body>
<h1>YouTube AI热门视频 · {YYYY-MM-DD} · 晚间档</h1>
<h2>最热门长视频 TOP 10</h2>
<p>本周上传，播放量+互动率综合评分排序</p>
<ol><li seq="auto"><a href="URL">标题</a> ｜频道：xxx ｜播放：xxx ｜时长：xxx ｜上传：xxx</li>...</ol>
<h2>最热门短视频 TOP 5</h2>
<ol><li seq="auto"><a href="URL">标题</a> ｜频道：xxx ｜播放：xxx ｜时长：xxx ｜上传：xxx</li>...</ol>
<h2>当日新发热门视频 TOP 10</h2>
<p>最近上传，按最新排序</p>
<ol><li seq="auto"><a href="URL">标题</a> ｜频道：xxx ｜播放：xxx ｜时长：xxx ｜上传：xxx</li>...</ol>
</body></docx>
```

### Bilibili 模板（方案A AI+全站分离结构）

```xml
<docx><title>Bilibili 热门视频</title><body>
<h1>每日Bilibili AI热门推送 · {YYYY-MM-DD} · 晚间档</h1>
<h2>最热门长视频 TOP 15</h2>
<p>AI相关热门视频排序</p>
<ol><li seq="1"><a href="URL">标题</a> | UP主：xxx | 播放：xxx | 点赞：xxx | 发布：YYYY-MM-DD | 综合评分：x.xxxx</li>...</ol>
<h2>最热门小视频 TOP 7</h2>
<ol><li seq="1"><a href="URL">标题</a> | ...</li>...</ol>
<h1>每日Bilibili全站热门推送 · {YYYY-MM-DD} · 晚间档</h1>
<h2>最热门长视频 TOP 15</h2>
<p>全站播放量排序</p>
<ol><li seq="1"><a href="URL">标题</a> | ...</li>...</ol>
<h2>最热门小视频 TOP 7</h2>
<ol><li seq="1"><a href="URL">标题</a> | ...</li>...</ol>
</body></docx>
```

---

## 飞书文档映射（当前有效）

> ⚠️ **重要**：完整的实时文档映射（含 Token、链接、cron job ID）已迁移至 `<references/feishu-doc-map.md>`。
> 本文件仅保留 YouTube 晚间档的**具体结构规范**（标题模板、内容格式），其他任务请参考 feishu-doc-map.md。

### YouTube AI 热门晚间档文档

| 文档标题 | Token | 链接 | cron Job ID |
|---------|-------|------|-------------|
| YouTube AI热门视频 · 晚间档 | `HhyMdusqdoVcW9xLyd2c2Yc2nnf` | https://zt854jxlft.feishu.cn/docx/HhyMdusqdoVcW9xLyd2c2Yc2nnf | `d470b5d9b593` |

完整 Token 映射和 cron job 列表见 `<references/feishu-doc-map.md>`。

---

## lark-cli 路径与参数规范

### 路径约束

`lark-cli --content @filepath` 必须满足以下条件之一：

1. **相对路径**（推荐）：文件放在 HERMES_AGENT_CWD（`/Users/xiesg/.hermes/hermes-agent/`），直接用文件名或 `./filename`：
   ```bash
   # 文件在 HERMES_AGENT_CWD 中
   --content @merged_bilibili.xml
   # 或显式相对路径
   --content @./merged_bilibili.xml
   ```

2. **从 HERMES_HOME 引用**（需完整相对路径）：
   ```bash
   # 从 /Users/xiesg/ 引用 .hermes/cron/output/ 下的文件
   --content @./.hermes/cron/output/file.xml
   ```

❌ **绝对路径报错**：`--content @/tmp/file.xml` 或 `--content @~/path` 均报错：
```
--content: invalid file path "/tmp/xxx": --file must be a relative path within the current directory
```

**临时文件处理**：当数据先写入 `/tmp/` 时，必须先 `cp` 到 HERMES_AGENT_CWD 再引用。

### cronjob Python 路径偏移

`os.path.expanduser("~/.hermes/cron/output/")` 在 cronjob 中展开为错误路径 `/Users/xiesg/.hermes/home/.hermes/cron/output/`（多了一层 `.hermes/home/`）。

**必须用硬编码绝对路径**：
```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
```

### lark-cli docs +update 参数（v2 API）

```bash
# 正确
lark-cli docs +update --api-version v2 \
  --doc "<doc_id>" \
  --command overwrite \
  --content @./.hermes/cron/output/file.xml \
  --doc-format xml

# 写入后追加（AI热门任务推荐）
lark-cli docs +update --api-version v2 \
  --doc "<doc_id>" \
  --command append \
  --content @./.hermes/cron/output/file.xml \
  --doc-format xml
```

⚠️ **常见错误**：`--mode append`（v1 参数），v2 API 必须用 `--command append`。

---

## 旧版结构（已废弃，目录空白）

```xml
<!-- ❌ 自定义标签无法生成飞书目录 -->
<section>📺 一、最热门长视频 TOP 10</section>
<item index="1"><title>...</title><link>...</link></item>
```