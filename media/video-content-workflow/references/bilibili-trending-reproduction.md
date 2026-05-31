# bilibili-trending 复现命令（2026-05-30 实测）

## 输出文件路径（重要）

**严禁写入 subagent 的 CWD（`hermes-agent/` 目录）。** 所有输出文件必须写入 `/Users/xiesg/workspace/work-outputs/`：

```python
output_dir = "/Users/xiesg/workspace/work-outputs/"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "bilibili-trending.xml")
```

**验证**：`ls /Users/xiesg/workspace/work-outputs/bilibili-trending*.xml`

> 注意：subagent 的 CWD 被设为 `/Users/xiesg/.hermes/hermes-agent/`，使用相对路径写入会导致文件落入该目录而非 workspace。

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

**⚠️ 无独立 API**，从 `type=all&order=hot` 列表按 `duration ≤ 60` 秒过滤：

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
