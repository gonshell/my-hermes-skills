# 飞书写入新发现（2026-05-29）

来源：cron job `1f4c7fb989aa`（每日Bilibili AI热门视频推送）调试会话。

---

## P1: XML 中的 `<title>` 标签会覆盖文档标题

**问题现象**：cron job 在 output.xml 里写了：
```xml
<title>Bilibili AI热门视频 (2026-05-29 21:02:55)</title>
<p>…正文…</p>
```
执行 `+update --command overwrite` 后，飞书文档标题变成了这个带时间戳的字符串（用户看到飞书文档标题一直在变）。

**根因**：`overwrite` 是全量替换——XML 中所有标签都会被飞书处理，`<title>` 标签会被飞书识别并覆盖文档标题。

**✅ 正确做法**：XML 内容**只包含正文块，不要包含 `<title>` 标签**。文档标题通过飞书界面来管理，不要在 XML 里嵌入时间戳。

```xml
<!-- Bilibili AI热门视频 | 2026-05-29 21:02:55 -->
<p>📺 一、最热门长视频 TOP 15（7天内，综合评分）</p>
<p>…正文…</p>
```

用 XML 注释 `<!-- ... -->` 而非 `<title>` 标签来标记时间戳版本，注释不会被飞书处理为标题。

---

## P2: `degrade_code=1011` = 写入未真正生效（revision_id 欺骗性变化）

**问题现象**：
- `+update overwrite` 返回 `revision_id` 从 5→6 变化（看似写入成功了）
- 但 `+fetch` 发现内容没有任何变化
- 原因是两次写入的内容几乎相同（同样的视频列表顺序），飞书认为"无变化"但仍更新了 revision

**返回结构**：
```json
{
  "ok": true,
  "result": "partial_success",
  "data": {
    "document": { "revision_id": 6, "url": "..." }
  },
  "warnings": ["degrade_code=1011,msg=Instruction produced no document changes..."]
}
```

**含义**：`degrade_code=1011` = "内容无变化，未真正写入"。

**判断真正成功的标准**：不能只看 revision_id，必须 `+fetch` 读取文档内容并比对是否有实际新增内容。

**根本原因分析**：cron job 每次抓取的 B站热门视频排序相似，导致 output.xml 内容和上次几乎相同 → 飞书判定为重复写入 → degrade_code=1011。

**解决方案**：在 output.xml 头部加入**当日时间戳作为注释块**，确保每次内容都不同，飞书就会真正写入：

```xml
<!-- Bilibili AI热门视频 | 2026-05-29 21:02:55 -->
<p>📺 一、最热门长视频 TOP 15（7天内，综合评分）</p>
<p>1. 视频标题 ...</p>
```

XML 注释 `<!-- ... -->` 每次都不同，内容就不同，`overwrite` 就能真正生效。

---

## 总结：cron job 写入飞书文档 Checklist

- [ ] output.xml 头部包含时间戳注释 `<!-- 2026-05-29 21:00 -->`（确保每次不同）
- [ ] output.xml **不包含** `<title>` 标签（避免覆盖文档标题）
- [ ] 写入后 `+fetch` 验证内容确实变了（不能只看 revision_id）
- [ ] 确认 lark-cli 命令使用相对路径 `@./filename`