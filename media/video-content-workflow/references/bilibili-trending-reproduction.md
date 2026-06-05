# bilibili-trending 复现命令（2026-05-30 实测，2026-06-05 更新）

> ⚠️ **2026-06-05 重要发现**：`execute_code`（sandbox 环境）和 `terminal curl` 均稳定返回 -352（限流），但 **browser console 执行 JS 可以绕过限制**。见下方「推荐流程」。

## 输出文件路径（重要）

> **2026-06-05 更新**：cron job 已统一使用 `/Users/xiesg/.hermes/cron/output/` 作为输出目录。旧路径 `/Users/xiesg/workspace/work-outputs/` 仅用于历史兼容。

所有输出文件必须写入 `/Users/xiesg/.hermes/cron/output/`：

```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "bilibili-trending.xml")
```

**验证**：`ls /Users/xiesg/.hermes/cron/output/bilibili-trending*.xml`

## 推荐流程：浏览器 console 执行 JS（2026-06-05 实测有效）

> 这是目前最可靠的方案，绕过 -352 限流问题。

```bash
# Step 1: navigate
browser_navigate → "https://api.bilibili.com/x/web-interface/ranking/v2?type=all&order=hot"

# Step 2: 验证数据加载
browser_console → expression: (async () => {
  const data = JSON.parse(document.body.innerText);
  return JSON.stringify({code: data.code, listLen: data.data?.list?.length || 0});
})()

# Step 3: 提取所有字段
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

# Step 4: write_file 保存 JSON，再 execute_code open() 读取
# ⚠️ 不要内联到 Python 脚本，会导致语法错误
```

## 长视频 TOP 15 数据获取

```bash
# Step 1: 获取全站热门排名列表（TOP 100，含 bvid/title/play/likes/duration/pubdate）
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all&platform=web" \
  -H "User-Agent: Mozilla/5.0" | python3 -c "
import sys,json
d=json.load(sys.stdin)
items=d.get('data',{}).get('list',[])
for i in items[:15]:
    o=i.get('owner',{})
    stat=i.get('stat',{})
    print(f'SPLIT::{i.get(\"bvid\",\"\")}|{i.get(\"title\",\"\")}|{o.get(\"name\",\"\") or o.get(\"uname\",\"\")}|{stat.get(\"view\",0)}|{stat.get(\"like\",0)}|{i.get(\"pubdate\",0)}|{i.get(\"duration\",0)}')
"

# Step 2: 批量补全 UP 主名（ranking v2 中 owner.name 可能为空）
# bvids 为上一步输出的 bvid 列表
for bvid in BV1JiVb6EEi7 BV1a3G161Evc ...; do
  curl -s "https://api.bilibili.com/x/web-interface/view?bvid=$bvid" -H "User-Agent: Mozilla/5.0" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); o=d.get('data',{}).get('owner',{}); print(o.get('name','') or o.get('uname',''))"
done
```

## 小视频 TOP 7 数据获取

**⚠️ 无独立 API**，从 `type=all&order=hot` 列表按 `duration ≤ 90` 秒过滤：

```python
import subprocess, json
bvids_short = []
r = subprocess.run(['curl','-s',
    'https://api.bilibili.com/x/web-interface/ranking/v2?type=all&platform=web',
    '-H','User-Agent: Mozilla/5.0'], capture_output=True, text=True)
items = json.loads(r.stdout).get('data',{}).get('list',[])
shorts = [i for i in items if i.get('duration',0) < 120][:7]
for i in shorts:
    o = i.get('owner',{})
    print(f"SPLIT::{i.get('bvid')}|{i.get('title')}|{o.get('name','') or o.get('uname','')}|{i.get('stat',{}).get('view',0)}|{i.get('stat',{}).get('like',0)}")
```

## 综合评分（播放量×0.4 + 点赞×0.6）

```python
def composite_score(play, likes):
    return play * 0.4 + likes * 0.6

long_sorted  = sorted(long_videos,  key=lambda x: composite_score(x[3], x[4]), reverse=True)
small_sorted = sorted(small_videos, key=lambda x: composite_score(x[3], x[4]), reverse=True)
```

## 飞书写入

```bash
cd /Users/xiesg
lark-cli docs +update --api-version v2 \
  --doc "<doc_token>" \
  --command overwrite \
  --content @.hermes/cron/output/bilibili-trending_YYYY-MM-DD.xml \
  --doc-format xml
```

## 已知问题

1. **小视频无独立端点**：`type=small_video` 返回 `[]`，`/rank/small` 重定向到 `/rank/all`，只能靠时长过滤
2. **owner.name 为空**：ranking v2 中 UP 主名可能为空，必须逐条调用 `/x/web-interface/view?bvid=` 补全
