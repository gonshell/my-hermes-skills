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
<docx><title>YouTube AI热门视频</title><body>
<h1>每日AI热门视频推送 · {YYYY-MM-DD} · 早间档</h1>
<h2>最热门长视频 TOP 10</h2>
<p>本周上传，播放量+互动率综合评分排序</p>
<ol><li seq="1"><a href="URL">标题</a> · 播放量 · 时间 · 频道名</li>...</ol>
<h2>最热门短视频 TOP 5</h2>
<ol><li seq="1"><a href="URL">标题</a> · 播放量 · 时间</li>...</ol>
<h2>当日新发热门视频 TOP 10</h2>
<p>本周新上传视频，按最新排序</p>
<ol><li seq="1"><a href="URL">标题</a> · 播放量 · 时间 · 频道名</li>...</ol>
<h1>每日AI热门视频推送 · {YYYY-MM-DD} · 晚间档</h1>
<h2>最热门长视频 TOP 10</h2>
<p>本周上传，播放量+互动率综合评分排序</p>
<ol><li seq="1"><a href="URL">标题</a> · 播放量 · 时间 · 频道名</li>...</ol>
<h2>最热门短视频 TOP 5</h2>
<ol><li seq="1"><a href="URL">标题</a> · 播放量 · 时间</li>...</ol>
<h2>当日新发热门视频 TOP 10</h2>
<p>本周新上传视频，按最新排序</p>
<ol><li seq="1"><a href="URL">标题</a> · 播放量 · 时间 · 频道名</li>...</ol>
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

| 文档标题 | Token | 链接 |
|---------|-------|------|
| YouTube AI热门视频 | `OoxcdJ72worwMHxwK73ctbdhn0b` | https://zt854jxlft.feishu.cn/docx/OoxcdJ72worwMHxwK73ctbdhn0b |
| Bilibili 热门视频 | `MjT6dT3abopHBpxkwPCcauGWn6e` | https://zt854jxlft.feishu.cn/docx/MjT6dT3abopHBpxkwPCcauGWn6e |

---

## cron 任务映射

| 任务 | Job ID | 时间 | 文档 Token | 写入模式 |
|------|--------|------|-----------|---------|
| YouTube AI早间档 | `fa294bf7d232` | 06:00 | `OoxcdJ72...` | overwrite |
| YouTube AI晚间档 | `d470b5d9b593` | 20:00 | `OoxcdJ72...` | overwrite |
| Bilibili AI热门 | `1f4c7fb989aa` | 21:00 | `MjT6dT3a...` | append |
| Bilibili 全站热门 | `0e9f3cb36fe6` | 22:00 | `MjT6dT3a...` | overwrite |

---

## lark-cli 路径与参数规范

### 路径约束

`lark-cli --content @filepath` 必须从 HERMES_HOME（`/Users/xiesg/`）用相对路径：

- ✅ `--content @.hermes/cron/output/file.xml`（从 HERMES_HOME 的 `.hermes/cron/output/` 目录）
- ❌ `--content @/absolute/path`（绝对路径报错）
- ❌ `--content @~/path`（波浪号路径报错）

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