# Browser Console 提取模板(2026-06-29 实测通过)

## 通用模式

所有提取都用 `browser_console` 执行 JS,返回 JSON 数组。
`browser_navigate` 访问 SPA 页面后,等 2-3 秒让 JS 渲染完成再执行。

## 模型页: `modelscope.cn/models?sort=latest`

```js
Array.from(document.querySelectorAll('a[href*="/models/"]'))
  .filter(a=>a.href.match(/\/models\/[^\/]+\/[^\/]+$/))
  .slice(0,20)
  .map(a=>({name:a.textContent.trim().replace(/\s+/g,' ').slice(0,100),href:a.href.split('?')[0]}))
```

**注意**:结果包含大量 LoRA 微调/社区量化版。过滤有意义的:
- 去掉名字里含 "LoRA" + 无知名厂商的条目
- 保留:新架构(MIM4D)、知名厂商首发(Cohere)、社区量化头部(Gemma4/Qwen3.5 MLX)

## 数据集页: `modelscope.cn/datasets?sort=latest`

```js
Array.from(document.querySelectorAll('a[href*="/datasets/"]'))
  .filter(a=>a.href.match(/\/datasets\/[^\/]+\/[^\/]+$/))
  .slice(0,20)
  .map(a=>({name:a.textContent.trim().replace(/\s+/g,' ').slice(0,100),href:a.href.split('?')[0]}))
```

**注意**:结果含提供方名+日期+下载量(嵌在文本里)。需手动解析提取。

## MCP 页: `modelscope.cn/mcp`

**总数**:页面搜索框 placeholder 包含总数 — `document.querySelector('input[placeholder*="共"]')?.placeholder`

**头部 MCP 服务**(按调用量排序):
```js
Array.from(document.querySelectorAll('main a'))
  .filter(a=>a.href.includes('/mcp/servers/'))
  .slice(0,15)
  .map(a=>{
    const t=a.textContent.trim().replace(/\s+/g,' ');
    const m=t.match(/(\d+\.?\d*[km])/);
    return {name:t.slice(0,100),href:a.href,usage:m?m[1]:''};
  })
```

**分类分布**:snapshot 里包含,直接从 `generic[ref=e20-e32]` 提取 StaticText。

**合作 banner**:`main a[href*="dingtalk" 或 "intel" 或 "siemens"]`

## 论文页: `modelscope.cn/papers`

```js
Array.from(document.querySelectorAll('main a[href*="/papers/"]'))
  .slice(0,15)
  .map(a=>({
    title:a.textContent.trim().replace(/\s+/g,' ').slice(0,100),
    arxiv:a.href.match(/\/papers\/(\S+)/)?.[1]||'',
    href:a.href.split('?')[0]
  }))
```

**注意**:结果第一段是中文摘要,第二段才是英文标题。取第一个句号前的内容作标题。

## arXiv API 备源

```
http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&max_results=20
```

返回 Atom XML。`<title>` 跳过第一条(feed 自身),后续为论文标题。
`<id>` 为论文链接。解析 regex: `r"<title>([^<]+)</title>"` + `r"<id>([^<]+)</id>"`

## 实测时间

2026-06-29 23:30。4 板块均拿到 10-20 条真实数据。MCP 总数 9,712。
