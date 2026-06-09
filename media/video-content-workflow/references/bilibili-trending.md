# bilibili-trending 参考（2026-05 修订，2026-05-31 更新）

> ⚠️ **2026-05-31 关键修正**：① `type=small`/`type=smallvideo` 返回 `-400`（不只是空数组）；② 小视频排序必须是"按播放量排序"（不是综合评分）；③ 时长阈值改为 `≤ 90` 秒（`≤ 60` 会漏掉60-90s短视频）。

## 与 bilibili-ai-trending 的区别

`bilibili-trending` 是**全站热门**（所有分类），`bilibili-ai-trending` 是 AI 领域特定热门。两者共享评分算法。

## 长视频 TOP 15

来源 `https://api.bilibili.com/x/web-interface/ranking/v2?type=all`，取 `data.list` 前15条（已按综合得分排序，过滤视频非小视频）。

## 小视频 TOP 7（2026-05 实测修正）

**⚠️ Bilibili 没有独立的小视频 API**。所有已知端点均不可用：
- `type=smallvideo` 参数 → 返回 `code: -400`（请求错误）
- `type=small_video` 参数 → 返回 `[]`（空数组）
- `/v/popular/rank/small` URL → 302 重定向到 `/v/popular/rank/all`
- `vc.bilibili.com/p/eden/rank` SPA → 需登录 Cookie，curl 无法直接获取
- `api.vc.bilibili.com/board/v1/ranking/top` → 302 重定向到 HTML 登录页

**正确方法**：从 `type=all&order=hot` 排序中按视频时长 `duration ≤ 90` 秒过滤，取前7条作为小视频。

> **阈值修正（2026-05-31）**：`duration ≤ 90` 比 `< 120` 更准确识别短视频内容。2026-05-31 实测：100条热门视频中 `duration ≤ 90` 的有27条，选出TOP 7 充裕。

## 热门榜单获取方法（2026-05-31 实测）

### 方法1：Bilibili 排行榜 API（推荐，2026-06 实测可用）

> ⚠️ **2026-06-04 修正**：ranking v2 API **没有废弃**，实测完全可用。之前的 -352 错误是因为缺少请求头或触发了频率限制。

必须携带完整请求头：

```bash
curl -s 'https://api.bilibili.com/x/web-interface/ranking/v2?type=all' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  -H 'Referer: https://www.bilibili.com/' | python3 -c "
import json,sys
data = json.load(sys.stdin)
for v in data['data']['list'][:5]:
    print(v['bvid'], v['title'], v['duration'])
"
```

注意：
- `type=all` 是唯一有效参数（`order=hot` 对 ranking v2 无效，是 search API 参数）
- 返回 100 条，按内置综合算法排序
- **大量数据不要内联到 Python 脚本**：先 `curl` 保存到 `/tmp/bilibili.json`，再用 `python3 open()` 读取
- `owner.name` / `owner.uname` 可能为空，需补全时加 0.2s delay 防限流

### 方法2：execute_code 批量获取 + 补全 UP 主名

```python
import urllib.request, json, time
# 1. 批量获取TOP100（一次请求）
url = "https://api.bilibili.com/x/web-interface/ranking/v2?type=all&order=hot"
req = urllib.request.Request(url, headers={'User-Agent': '...', 'Referer': 'https://www.bilibili.com/'})
with urllib.request.urlopen(req, timeout=15) as resp:
    items = json.loads(resp.read())['data']['list']
# 2. 按duration分离长短视频
long_videos, short_videos = [], []
for item in items:
    entry = {'bvid': item['bvid'], 'title': item['title'],
             'up': item.get('owner',{}).get('name','') or item.get('owner',{}).get('uname',''),
             'play': item.get('stat',{}).get('view',0), 'duration': item.get('duration',0)}
    (short_videos if item['duration'] <= 60 else long_videos).append(entry)
# 3. 补全空UP主名（批量+0.2s延迟防限流）
empty_up = [v for v in long_videos + short_videos if not v['up']]
for v in empty_up:
    url2 = f"https://api.bilibili.com/x/web-interface/view?bvid={v['bvid']}"
    with urllib.request.urlopen(urllib.request.Request(url2, headers={...})) as resp2:
        v['up'] = json.loads(resp2.read())['data']['owner']['name']
    time.sleep(0.2)
```

### 方法3：浏览器 console 执行 JS（2026-06 实测有效）

>⚠️ **2026-06-05 关键发现**：`execute_code`（sandbox 环境）和 `terminal curl` 均返回 -352 限流，但 **browser console 执行 JS 可以直接读取完整 JSON**。这是目前最可靠的方案。

```javascript
// Step 1: navigate
browser_navigate → "https://api.bilibili.com/x/web-interface/ranking/v2?type=all&order=hot"

// Step 2: 验证数据加载
browser_console → expression: (async () => {
  const data = JSON.parse(document.body.innerText);
  return JSON.stringify({code: data.code, listLen: data.data?.list?.length || 0});
})()

// Step 3: 提取所有字段
browser_console → expression: (async () => {
  const data = JSON.parse(document.body.innerText);
  const list = data.data.list;
  return JSON.stringify(list.map(v => ({
    bvid: v.bvid, title: v.title,
    up: v.owner?.name || v.owner?.uname || '',
    play: v.stat?.view || 0, duration: v.duration || 0,
    link: v.short_link_v2 || `https://www.bilibili.com/video/${v.bvid}`
  })));
})()

// Step 4: 通过 write_file 保存 JSON 到临时文件，再用 execute_code open() 读取
// ⚠️ 不要把大数据内联到 Python 脚本，会导致语法错误
```

### 方法4：Web 搜索（备用）

当 API 不可用时，用 `mcp_minimax_web_search` 搜索 `bilibili热门视频 AI大模型 2025 site:bilibili.com`。

## API 响应字段参考（2026-05 实测）

### 长视频 ranking v2（`/x/web-interface/ranking/v2?type=all`）
```json
{
  "bvid": "BVxxxx",
  "title": "视频标题",
  "owner": { "name": "UP主名", "uname": "UP主名" },
  "stat": { "view": 播放数, "like": 点赞数 },
  "duration": 秒数,
  "pubdate": Unix时间戳（秒）
}
```
> ⚠️ `ranking v2` 接口中 `owner.name` / `owner.uname` 经常为空字符串（约30%的视频），必须对每个 bvid 调用 `/x/web-interface/view?bvid=xxx` 补全 UP 主名。这也是触发 -352 限流的主要原因之一（逐个请求view接口）。**解决：批量请求 ranking v2 获取完整列表，再用0.2s延迟逐个补全空值**。
## 小视频 TOP 7

无独立端点。从 `type=all` 列表中按 `duration ≤ 90` 秒过滤（2026-05-31 实测：100条中27条满足，选TOP 7 充裕）。

> ⚠️ **排序方式必须为"按播放量排序"**（任务要求），不是综合评分。过滤后按 `stat.view` 降序取前7。

## 综合评分算法（仅用于长视频排序）

长视频使用 `score = play * 0.4 + likes * 0.6` 排序。小视频不使用此算法。

```python
score = play * 0.4 + likes * 0.6
```
用于长视频和小视频分别排序后写入 XML。

## 飞书文档写入（DocxXML 格式规范）

> ⚠️ **2026-06-08 关键修正**：lark-cli `--doc-format xml` 期望 **DocxXML 格式**，即 `<docx><title>...</title><body>...</body></docx>` 结构。**不能用自定义 XML 根节点**（如 `<BilibiliTrending>`），否则飞书将标签转义为纯文本，目录功能失效。2026-06-08 实测返回警告：`Unsupported tag <BilibiliTrending> was escaped`。

### 正确格式 ✅

```xml
<docx><title>B站全站热门视频</title><body>
<h1>B站全站热门视频 · {YYYY年MM月DD日}</h1>

<h2>热门长视频 TOP 15</h2>
<p>按播放量排序</p>
<ol><li seq="auto"><a href="链接">标题</a> ｜UP主：xxx ｜播放：xxx ｜时长：xxx</li>...</ol>

<h2>热门小视频 TOP 7</h2>
<p>按播放量排序</p>
<ol><li seq="auto"><a href="链接">标题</a> ｜UP主：xxx ｜播放：xxx ｜时长：xxx</li>...</ol>

</body></docx>
```

### 错误格式 ❌

```xml
<!-- ❌ 自定义根节点 + XML 声明会导致标签被飞书转义为纯文本 -->
<?xml version="1.0" encoding="UTF-8"?>
<BilibiliTrending>
<title>B站全站热门视频</title>
<h1>B站全站热门视频 · {日期}</h1>
...
</BilibiliTrending>
```

### 写入命令

```bash
# 工作目录：HERMES_HOME (/Users/xiesg/)
# 临时文件写入 HERMES_HOME 根目录，lark-cli 从相对路径读取
lark-cli docs +update --api-version v2 \
  --doc "TcjbdsX0ToprvCxXPbQcbLqknTq" \
  --command overwrite \
  --content @./merged_bilibili.xml \
  --doc-format xml
```

⚠️ `--content @/absolute/path` 和 `--content @~/path` 均报错：`--file must be a relative path within the current directory`。文件必须在 HERMES_HOME 下，用 `@./filename.xml` 引用。
```