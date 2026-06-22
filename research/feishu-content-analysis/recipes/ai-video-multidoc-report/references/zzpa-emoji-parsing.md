# ZzPa B站工具合集 Doc 解析配方

## 文档结构

ZzPa (`ZzPad3g4NotV9OxUO9WcLTpAnEd`) 是 B 站 AI 工具视频合集，7 天 × 每日 TOP 27。

### 结构陷阱

ZzPa 有 24 个 `<h2>日期</h2>` section，但**每个日期 section 几乎是空的**（只有 `<hr/>` 分隔线）。

真正内容在两种 section 里：
- `📺 一周内新发 · 最热门长视频 TOP 20`
- `🎵 一周内新发 · 最热门短视频 TOP 7`

每对 section 重复 7-8 次（每天一组），总计约 216 条。

### 条目格式（emoji 元数据）

ZzPa 的条目格式与其他 video doc **完全不同**：

```html
<p><b>1.</b> 视频标题</p>
<blockquote>
  <p>👤 UP主名 ｜ 🎬 1:14 ｜ 👀 <b>2687</b> ｜ ❤️ 645 ｜ 📅 0天前
  <br/>🔗 <a href="https://www.bilibili.com/video/BV1xxx">链接</a>
  <br/>🏷️ deepseek</p>
</blockquote>
```

**关键区别**：
| 字段 | EBHD/HHYM/VIRB 格式 | ZzPa 格式 |
|---|---|---|
| 列表 | `<li>` | `<p><b>N.</b>` + `<blockquote>` |
| UP主 | `频道：xxx` 或 `UP主：xxx` | `👤 xxx ｜` |
| 播放量 | `播放：xxx` | `👀 <b>xxx</b> ｜` |
| 时长 | `时长：xxx` | `🎬 xxx ｜` |
| 点赞 | 无 | `❤️ xxx ｜` |
| 日期 | `上传：xxx` | `📅 xxx天前` |
| 标签 | 无 | `🏷️ xxx` |

## 完整解析代码

```python
import re

def parse_zzpa(raw_xml):
    """解析 ZzPa B站工具合集 doc。返回视频列表。"""
    videos = []
    for num, title, meta in re.findall(
        r'<p><b>(\d+)\.\s*</b>\s*(.*?)</p>\s*<blockquote>(.*?)</blockquote>',
        raw_xml, re.S
    ):
        title = re.sub(r'<[^>]+>', '', title).strip()
        mc = re.sub(r'<[^>]+>', ' ', meta)
        
        channel = re.search(r'👤\s*(.+?)\s*｜', mc)
        duration = re.search(r'🎬\s*(.+?)\s*｜', mc)
        views    = re.search(r'👀\s*(.+?)\s*｜', mc)
        likes    = re.search(r'❤️\s*(.+?)\s*｜', mc)
        upload   = re.search(r'📅\s*(.+?)(?:\s*｜|\s*$)', mc)
        tag      = re.search(r'🏷️\s*(.+?)(?:\s*$)', mc)
        url      = re.search(r'href="?(https://www\.bilibili\.com/video/[^"\\]+)', meta)
        bv       = re.search(r'/(BV[a-zA-Z0-9]+)', meta)
        
        videos.append({
            'num': int(num),
            'title': title,
            'url': url.group(1) if url else '',
            'video_id': bv.group(1) if bv else '',
            'channel': channel.group(1).strip() if channel else '',
            'views': views.group(1).strip() if views else '',
            'duration': duration.group(1).strip() if duration else '',
            'upload': upload.group(1).strip() if upload else '',
            'likes': likes.group(1).strip() if likes else '',
            'tag': tag.group(1).strip() if tag else '',
        })
    return videos
```

## 去重

ZzPa 216 条里有 47 组重复标题（同一视频在不同日期上榜）。

```python
from collections import Counter

def dedup_zzpa(videos):
    """按标题前 25 字符去重，保留播放量最高的版本。"""
    seen = {}
    for v in videos:
        key = v['title'][:25]
        pv = parse_views(v['views'])
        if key not in seen or pv > seen[key][1]:
            seen[key] = (v, pv)
    return [x[0] for x in sorted(seen.values(), key=lambda x: x[1], reverse=True)]
```

## 标签分布（2026-06-21 实测）

```
deepseek: 90 (42%)
chatgpt: 38 (18%)
claude: 19 (9%)
大模型: 20 (9%)
llm: 17 (8%)
qwen: 11 (5%)
ai编程: 9 (4%)
ai agent: 7 (3%)
```

## 播放量 TOP 5（去重后）

| 标题 | UP主 | 播放量 | 标签 |
|---|---|---|---|
| Claude Fable 5 首发实测 | 程序员鱼皮 | 30.5万 | claude |
| Deepsek登顶美榜第一！ | 军武-那兔 | 23.0万 | deepseek |
| 《豆包和deepseek聊天记录》 | 吟游实人 | 16.2万 | deepseek |
| DeepSeek 正式上线"识图模式" | 黑鸦Heya | 8.3万 | deepseek |
| 这才是 DeepSeek 真正的黑科技 | 差评前沿部 | 8.3万 | deepseek |
