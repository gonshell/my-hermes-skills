# lark-doc 踩坑记录（补充）

> ⚠️ 本文件是 lark-doc-pitfalls skill 的补充，遇到飞书文档操作问题时先查此处。

---

## 15. `<title>` 标签的正确用法（2026-05-30 已修正）

**旧规则（错误）**：禁止在 XML 内容中使用 `<title>` 标签，否则会导致文档标题为 "Untitled"。
**正确规则**：飞书文档标题从 XML 内容中的 `<title>` 标签自动提取。**必须包含有意义的 `<title>` 标签**。

| XML 内容 | 文档标题 |
|---------|---------|
| `<title>项目计划</title><p>内容</p>` | ✅ "项目计划" |
| `<title></title><p>内容</p>` | ❌ "Untitled" |
| `<title>Untitled</title><p>内容</p>` | ❌ "Untitled" |
| 无 `<title>` 标签 | ❌ "Untitled" |

**正确 XML 结构示例**：
```xml
<title>Bilibili全站热门</title>
<!-- 每日Bilibili全站热门视频推送 | 2026-05-30 22:00:00 -->
<h1>📺 一、最热门长视频 TOP 15</h1>
<p>1. 视频标题 ...</p>
...
```

**关键**：cron 定时任务写入飞书文档时，XML 内容中**必须包含** `<title>任务名</title>` 标签，且 title 内容不能为 "Untitled" 或空。

**来源**：2026-05-30 实测发现。创建文档时 `--title` 参数在 v2 API 不存在，v1 API 不生效；但 XML 内容中的 `<title>` 标签可以正确设置文档标题。

---

## 16. `--new-title` 参数不生效

**现象**：`lark-cli docs +update --new-title "xxx"` 传入后文档标题不变。

**说明**：
- v1 API：`--new-title` 参数传入不报错，写入返回 `success`，revision 增加，但 `+fetch` 返回 `title: null`，文档 UI 标题不变
- v2 API：`+update` 根本不支持 `--new-title` 参数

**正确做法**：通过 XML 内容中的 `<title>` 标签设置文档标题，不要依赖 `--new-title` 参数。

---

*最后更新：2026-05-30*