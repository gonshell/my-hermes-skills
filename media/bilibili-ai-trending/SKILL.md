---
name: bilibili-ai-trending
description: 获取Bilibili上AI领域的热门视频和当日新发视频，返回标题、URL、播放量、简单摘要。使用browser工具从B站搜索页面提取数据。
triggers:
  - 获取B站今日热门AI视频
  - Bilibili AI视频排行
  - B站 AI领域热门长视频/短视频
  - 当天新发AI视频
---

# Bilibili AI 热门视频获取

## 功能说明
获取Bilibili上AI领域的热门视频和当日新发视频，返回标题、URL、播放量、简单摘要。

## 数据分类

### 1. 最热门长视频 TOP 15
- 搜索词：`AI LLM GPT ChatGPT Claude Qwen Deepseek`
- 过滤器：视频（非小视频）
- **时间范围：3天内发布**
- **综合评分排序**

### 2. 最热门小视频 TOP 7
- Bilibili的"小视频"频道
- **时间范围：3天内发布**
- **综合评分排序**

### 3. 当日新发热门视频（3天内）
- 长视频 TOP 5：按最新发布排序，筛选播放量较高的
- 短视频 TOP 3：按最新发布排序

## 综合评分算法

```
score = 0.5 × log₁₀(播放量)/10
      + 0.35 × min(点赞/播放 × 10, 1.0)
      + 0.15 × 关键词新鲜度
```

### 计算公式说明

| 权重 | 指标 | 计算方式 |
|------|------|----------|
| 50% | 播放量 | `0.5 × log₁₀(播放量) / 10` — 对数归一化，避免头部视频垄断 |
| 35% | 互动率 | `0.35 × min(点赞/播放 × 10, 1.0)` — 点赞/播放比，cap at 1.0 |
| 15% | 新鲜度 | `0.15 × max(1 - 发帖小时数/168, 0)` — 7天内线性衰减 |

### 数据提取字段要求
必须提取以下字段用于评分：
- `播放量`（views）
- `点赞数`（likes）
- `发布时间`（publish time，用于计算新鲜度）
- `标题`（title）

### 评分计算实现
```python
import math
from datetime import datetime, timedelta

NOW = datetime(2026, 5, 10)  # 在cron job中设置为当前时间

def calc_score(views, pub_date, current_date=NOW, max_views=10_000_000):
    """
    综合评分: 0.5 × log_views + 0.15 × freshness (+ 0.35 × 互动率, 通常=0)
    无点赞数据时互动率为0。
    新鲜度7天(168h)线性衰减至0。
    """
    if pub_date is None:
        return 0
    hours_old = (current_date - pub_date).total_seconds() / 3600
    freshness = max(1 - hours_old / 168, 0)
    log_score = math.log10(views + 1) / math.log10(max_views)
    # Interaction = 0 when likes unavailable (B站搜索页不提供点赞数)
    score = 0.5 * log_score + 0.15 * freshness
    return score
```

⚠️ **实际应用注意**：B站搜索页几乎不提供点赞数，互动率权重(0.35)实际上为0，真实公式为 `0.5×log + 0.15×freshness`。对于超过7天的历史视频（freshness=0），score几乎完全由播放量决定，因此长期热门内容（如月映万川_Boo的"全球六大顶级AI白嫖"合集，50万播放）会持续排在前列。

### 注意事项
- B站搜索结果页面通常不直接显示点赞数，需要进入视频详情页获取
- 如果无法获取点赞数，则只使用播放量和新鲜度计算（归一化为满分1.0）
- 新鲜度基准：发布时间在7天以内，之外则为0

## 搜索URL模板

⚠️ **B站 duration 参数全部失效（2026年5月确认）**，以下URL已不可靠。使用底部的实测有效URL。

```
# ⚠️ 以下URL的 duration 参数在非登录态下全部失效，仅作历史参考

# 3天内最热门长视频（按播放量）— duration=4 失效，返回全时间段视频
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=click&duration=4

# 3天内最热门小视频 — tids=124 也失效
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=click&tids=124&duration=4

# 3天内最新发布长视频 — duration=4 失效
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=pubdate&duration=4

# 3天内小视频最新发布
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=pubdate&tids=124&duration=4
```

### ✅ 实测有效的搜索URL（2026年5月14日验证）

```bash
# 最佳：宽泛中文关键词 + 按发布日期排序（无duration，返回分钟级最新内容）
https://search.bilibili.com/video?keyword=AI%20%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&order=pubdate

# 补充：大模型+深度学习聚焦
https://search.bilibili.com/video?keyword=AI%20%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%20%E6%B7%B1%E5%BA%A6%E5%AD%A6%E4%B9%A0&order=pubdate

# 补充：LLM模型名（结果少但精准）
https://search.bilibili.com/video?keyword=DeepSeek%20GPT%20Claude%20Qwen%20LLM%20%E5%A4%A7%E6%A8%A1%E5%9E%8B&order=pubdate
```

### B站时间筛选参数（⚠️ 全部失效）
- `duration=1`：视频时长10分钟内（不是"1天内"！），会过滤掉长视频
- `duration=2`：一天内 — 失效
- `duration=3`：一周内 — 失效，2026年5月实测返回2022年视频
- `duration=4`：3天内 — 失效

## 输出格式

```
📺 一、最热门长视频 TOP 15（3天内，综合评分）

1. 视频标题
   播放量：XXX | 发布时间 | UP主 | 综合评分
   https://www.bilibili.com/video/BVxxxxxx

...

📺 二、最热门小视频 TOP 7（3天内，综合评分）

1. 视频标题
   播放量：XXX | 发布时间 | UP主 | 综合评分
   https://www.bilibili.com/video/BVxxxxxx

...

📺 三、当日新发热门视频（3天内）

### 长视频 TOP 5
1. 视频标题
   播放量：XXX | 发布时间 | UP主
   https://www.bilibili.com/video/BVxxxxxx

### 小视频 TOP 3
1. 视频标题
   播放量：XXX | 发布时间 | UP主
   https://www.bilibili.com/video/BVxxxxxx

---

📝 摘要说明
- 当前热门主题分析
- 关键趋势总结
```

## 链接显示注意事项
⚠️ 飞书消息中Markdown表格格式会导致链接无法点击显示，必须使用纯文本格式发送链接。

## 数据提取方法

### 长视频数据提取（搜索结果页）

**⚠️ 重要：browser_console 不支持具名 function 声明，必须使用匿名函数**

```javascript
var cards = document.querySelectorAll('.bili-video-card, .video-item');
var r = [];
cards.forEach(function(c, i){
  var a = c.querySelector('a[href*="/video/BV"]');
  if(!a) return;
  var link = a.href;
  var title = c.querySelector('h3')?.textContent?.trim() || '';
  if(!title) return;
  // 作者和日期在另一个<a>标签中，格式为"UP主名 · 日期"
  var allLinks = c.querySelectorAll('a');
  var author = '', date = '';
  allLinks.forEach(function(l){
    var txt = l.textContent.trim();
    if(txt && txt.includes('·') && !txt.includes('bilibili') && !txt.includes('http')){
      var parts = txt.split('·');
      if(parts.length >= 2){
        author = parts[0].trim();
        date = parts.slice(1).join('·').trim();
      }
    }
  });
  // 播放量从主链接文本中提取（注意：可能和时长混在一起，如"4万707:21"）
  var txt = a.textContent;
  var idx = txt.indexOf(' ');
  var views = idx > 0 ? txt.substring(0, idx).trim() : txt.trim();
  views = views.replace(/[^\d.万]/g, '');
  r.push({title: title, link: link, author: author, views: views, date: date});
});
JSON.stringify(r);
```

### 播放量解析（用于后续计算）
```javascript
// 在 Python 或后续处理中使用
function parseViews(text) {
  if (!text) return 0;
  text = text.toString().replace(/播放|·/g, '').trim();
  if (text.includes('万')) {
    return parseFloat(text) * 10000;
  }
  return parseInt(text) || 0;
}
```

### ✅ 最佳提取方法：BV链接 + h3标题（2026年5月15日验证）

**第一步：提取BV ID + 原始链接文本（播放量+弹幕+时长）**

这是最可靠的方式——直接从页面所有 `/video/BV` 链接中提取：
```javascript
// 提取所有视频卡片的BV号和原始文本
var r = [];
var seen = {};
var topLinks = document.querySelectorAll('a[href*="/video/BV"]');
topLinks.forEach(function(a){
  var href = a.href;
  var bvMatch = href.match(/BV[\w]+/);
  if(!bvMatch || seen[bvMatch[0]]) return;
  seen[bvMatch[0]] = true;
  var text = a.textContent.trim();
  r.push({bv: bvMatch[0], raw: text.substring(0, 200)});
});
JSON.stringify(r);
// 返回格式: {bv: "BV1fc5q6MEnL", raw: "稍后再看146019:11"}
// raw = "稍后再看" + 播放量 + 弹幕数 + 时长(HH:MM:SS 或 MM:SS)
```

**第二步：提取标题 + 作者 + 日期**

用 h3 标签定位标题，向上遍历找到作者/日期：
```javascript
var r = [];
var h3s = document.querySelectorAll('h3');
h3s.forEach(function(h){
  var title = h.textContent.trim();
  if(!title) return;
  var titleLink = h.closest('a');
  var bv = '';
  if(titleLink && titleLink.href) {
    var m = titleLink.href.match(/BV[\w]+/);
    bv = m ? m[0] : '';
  }
  // 作者/日期在父级的兄弟 <a> 中，格式 "UP主名 · 日期"
  var parent = h.parentElement.parentElement;
  var author = '', date = '';
  var allAs = parent.querySelectorAll('a');
  allAs.forEach(function(a){
    var txt = a.textContent.trim();
    if(txt.includes('·') && txt.length < 80){
      var p = txt.split('·');
      author = p[0].trim();
      date = p.slice(1).join('·').trim();
    }
  });
  r.push({t: title.substring(0,80), bv: bv, a: author, d: date});
});
JSON.stringify(r);
```

**第三步：在 Python 中合并两步数据，按 BV 关联**

### ⚠️ 关键陷阱：初始快照 vs 滚动后提取

- **初始页面快照**（browser_navigate 返回）包含正确的作者+日期信息
- **滚动后**，用 `parentElement × N` 向上遍历DOM会导致scope过大，所有视频的author都变成同一个值
- **最佳策略**：从初始快照手动记录作者/日期，从 `a[href*="/video/BV"]` 提取BV+播放量，最后在Python中合并

### 备用标题提取（当 card 选择器失败时）
```javascript
var h3s = document.querySelectorAll('h3');
var r = [];
for(var i=0; i<Math.min(h3s.length, 20); i++){
  var h = h3s[i];
  var title = h.textContent.trim();
  var pl = h.closest('a');
  var link = pl ? pl.href : '';
  if(title && link) r.push({title: title, link: link});
}
JSON.stringify(r);
```

## 已知问题

### 1. 搜索结果被截断
- B站搜索结果默认加载有限，需要滚动触发懒加载
- 使用 `browser_scroll(direction='down')` 多次滚动后提取

### 2. 小视频（tids=124）过滤不可靠
- `tids=124` 参数在 browser 环境下不能稳定生效，URL 会被重定向
- **替代方案**：从主搜索结果中按视频时长筛选（短时长≈小视频），或使用备选方案（Bing视频搜索）

### 3. 播放量显示格式
- B站常用单位：万（1.2万），但与时长可能粘连（如"4万707:21"）
- 需要用正则 `replace(/[^\d.万]/g, '')` 清理

### 4. browser_console 中不能使用具名函数
- `function parseViews(){}` 会报 SyntaxError
- 所有函数必须内联为匿名函数，或在外部定义

### 5. 作者/日期提取
- 作者和日期不在主视频卡片的主链接中
- 需要查找包含 "·" 分隔符的子链接元素

### 6. querySelectorAll 可能返回空结果
- `.bili-video-card` 在某些页面状态下可能返回 0 结果
- 备用方案：使用 `h3` 标签作为标题锚点，配合 `closest('a')` 向上查找链接

## 摘要生成
根据视频标题和描述生成2-3句话的简单摘要，说明视频主要内容。

## ⚠️ Bilibili 不可用时的备选方案

**备选方案：Bing视频搜索**
```
URL: https://www.bing.com/videos/search?q=AI+2026+trending+video+GPT+Claude+Deepseek+Bilibili
```

## 🔧 关键发现与故障排除（2026年4月实测）

### 1. 所有 duration 参数均失效（重要！2026年5月14日实测确认）
- **问题**：`duration=1/2/3/4` 在 browser 环境下全部失效，返回全时间段视频
- **duration=4**（3天内）：返回2024-2025年视频
- **duration=3**（一周内）：同样返回2022-2025年视频，完全忽略时间过滤
- **duration=1**（10分钟以下）：注意！这个参数含义是"视频时长≤10分钟"，不是"1天内"！用了反而会过滤掉长视频
- **原因**：B站搜索API的日期过滤在非登录态/headless环境下完全失效
- **状态**：2026年5月14日实测仍完全失效，无改善迹象
- **⚠️ 关键结论：不要使用任何 duration 参数！**

### 1b. 实测有效的搜索策略（2026年5月14日验证）

**最佳方案：`order=pubdate` + 宽泛中文关键词 + 无 duration 参数**

```bash
# ✅ 最佳：通用AI中文词 + 按发布日期排序（无duration参数）
# 返回分钟级最新内容（"14分钟前"、"1小时前"等相对时间戳）
https://search.bilibili.com/video?keyword=AI%20%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&order=pubdate

# ✅ 补充：更细分的关键词（返回较少但更精准）
https://search.bilibili.com/video?keyword=AI%20%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%20%E6%B7%B1%E5%BA%A6%E5%AD%A6%E4%B9%A0&order=pubdate

# ✅ 补充：LLM模型相关（结果较少但更聚焦）
https://search.bilibili.com/video?keyword=DeepSeek%20GPT%20Claude%20Qwen%20LLM%20%E5%A4%A7%E6%A8%A1%E5%9E%8B&order=pubdate

# ❌ 无效：order=click 返回全时间热门视频（无法按日期过滤）
# ❌ 无效：加 duration=1 会过滤到10分钟以下的短视频
# ❌ 无效：关键词加"2026年"只是标题匹配，不保证内容是最近的
```

**推荐工作流：**
1. 先用 `order=pubdate` + `AI 人工智能` 获取最新视频（scroll 3次，提取全部数据）
2. 在 Python 中用 `parse_bilibili_date()` 解析相对日期
3. 按 freshness > 0（7天内）过滤
4. 按 calc_score() 排序
5. 按时长分类长/短视频

**关键词选择策略：**
- `AI 人工智能` → 最宽泛，结果最多，能捕获"X分钟前"的最新内容
- `AI 人工智能 大模型 深度学习` → 稍窄，更聚焦大模型
- `DeepSeek GPT Claude Qwen LLM 大模型` → 精准但结果少，很多是旧视频因为标题匹配
- 不要在关键词中加"2026年"——这只是标题文本匹配，反而会漏掉不包含年份的最新视频

### 2. 播放量 + 视频时长混合字段解析（2026年5月实测修正）
- **DOM格式**：`"1.3万250932"` 或 `"4万70721"` — 播放量、点赞数、时长三者粘连！
- **真实格式**：`"1.3万" + "25" + "09:32"` → 播放量=1.3万，时长=25:09:32
- **解析规则**：
  - 第一个空格前 = 播放量（可能是 `1.4万` 或 `4245`）
  - 时长格式为 `HHMMSS` 或 `MMDDSS`，没有分隔符直接拼接在播放量后面
  - **⚠️ 必须用正则提取时长**：`/(\d{1,2}):(\d{2}):(\d{2})$/` 或 `/(\d{1,2}):(\d{2})$/`
  - 时长如果出现 `25:09:32`（>24小时）或 `09:32`（分钟），说明是视频总时长
- **python解析实现**（⚠️ 2026-05-15 修正：必须split取第一个token）：
  ```python
  def parse_views_and_duration(text):
      """解析 '稍后再看67 15 03:23:15' → views=67, duration='03:23:15'
      格式: 稍后再看 + 播放量(VV) + 弹幕数(DD) + 时长
      """
      if not text: return 0, ''
      text = text.strip().replace('稍后再看', '')
      m = re.search(r'(\d{1,2}):(\d{2}):(\d{2})\s*$', text)
      if m:
          h, mn, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
          duration = f"{h}:{mn:02d}:{s:02d}"
          num_part = text[:m.start()].strip()
      else:
          m2 = re.search(r'(\d{1,2}):(\d{2})\s*$', text)
          if m2:
              mn, s = int(m2.group(1)), int(m2.group(2))
              duration = f"{mn}:{s:02d}"
              num_part = text[:m2.start()].strip()
          else:
              duration = ''
              num_part = text.strip()
      # ⚠️ 关键: num_part可能是 "67 15" (播放量+弹幕)，必须只取第一个token
      tokens = num_part.strip().split()
      first_token = re.sub(r'[^\d.万]', '', tokens[0]) if tokens else ''
      if '万' in first_token:
          views = float(first_token.replace('万','')) * 10000
      else:
          views = int(float(first_token)) if first_token else 0
      return views, duration
  ```
    return views, duration
  ```
- **重要**：时长 > 24h 意味着B站视频时长格式为 `HH:MM:SS`（可能超过24小时）

### 3. 日期解析（相对日期 → 实际日期）
Bilibili 搜索结果使用相对日期格式，必须转换：
| 显示格式 | 含义 | 转换结果（假设2026-05-14） |
|----------|------|--------------------------|
| `14分钟前` | 几分钟前 | 2026-05-14（当天） |
| `昨天` | 昨天 | 2026-05-13 |
| `3小时前` / `刚刚` | 几小时前 | 2026-05-14（当天） |
| `前天` | 前天 | 2026-05-12 |
| `04-20` | 月-日 | 2026-04-20（如月<=当前月则当年，否则去年） |

⚠️ **CRITICAL BUG FOUND (2026-05-16 session)**: Original parser did NOT handle "N分钟前" format.
Videos like "1分钟前" returned `None` → excluded from all recent results silently.
必须在 `小时前` 检查之前先检查 `分钟前`。

```python
def parse_bilibili_date(date_str, current_date=datetime(2026, 5, 16, 21, 0)):
    """
    Parse Bilibili relative date → (datetime_obj, display_string).
    ⚠️ Must handle '分钟前' BEFORE '小时前' — order matters!
    """
    if not date_str:
        return None, None
    date_str = date_str.strip()

    # "N分钟前" — MUST check before "N小时前"
    if '分钟前' in date_str:
        try:
            mins = int(re.search(r'(\d+)', date_str).group(1))
            pub_date = current_date - timedelta(minutes=mins)
            return pub_date, date_str
        except:
            pass

    # "N小时前"
    if '小时前' in date_str:
        try:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            pub_date = current_date - timedelta(hours=hours)
            return pub_date, date_str
        except:
            pass

    if date_str == '刚刚':
        return current_date, '刚刚'
    if date_str == '昨天':
        pub_date = current_date - timedelta(days=1)
        return pub_date, '昨天'
    if date_str == '前天':
        pub_date = current_date - timedelta(days=2)
        return pub_date, '前天'

    # MM-DD format (e.g. "03-17")
    if re.match(r'^\d{2}-\d{2}$', date_str):
        try:
            m, d = map(int, date_str.split('-'))
            year = current_date.year
            pub_date = datetime(year, m, d)
            return pub_date, date_str
        except:
            return None, date_str

    # YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            pub_date = datetime.strptime(date_str, '%Y-%m-%d')
            return pub_date, date_str
        except:
            return None, date_str

    return None, date_str
```

**重要**：返回两个值 — (datetime对象, 原始/格式化字符串)，因为 `昨天` 这种相对日期需要保留用于显示，但在计算freshness时必须用datetime。

### 4. 长视频 vs 小视频分类阈值
- **B站标准**：小视频通常 ≤ 5分钟（300秒）
- **建议阈值**：`duration_sec <= 300` 归为小视频
- **注意**：`tids=124`（小视频分区）参数不可靠，不要依赖

### 5. browser_console 具名函数限制
- **错误**：`function parseViews(){}` → SyntaxError
- **解决**：所有函数必须内联为匿名函数，或在 Python 端处理解析逻辑
- **推荐**：在 Python/execute_code 中做数据清洗，browser_console 只负责提取原始文本

### 6. 滚动加载后数据不更新
- 滚动后 DOM 结构可能不变，但实际内容已懒加载
- 每次滚动后重新执行提取脚本，确保捕获新加载的视频卡片
- 建议滚动2-3次，每次等待页面响应

### 7. order=click（按播放量排序）无法获取近期热门
- **问题**：`order=click` 返回全时间段播放量最高的视频，不受任何 duration 参数约束
- **实测**：`keyword=AI 人工智能&order=click&duration=4` 返回2020-2025年的全站热门视频
- **解决方案**：只能通过 `order=pubdate` 获取最新视频，然后在代码中按播放量排序
- **⚠️ 这意味着无法直接获取"近期最热门"视频**——只能在最新视频中找播放量较高的

### 8. 播放量提取的 a.textContent 包含标题文本（2026年5月确认）
- **问题**：`c.querySelector('a[href*="/video/BV"]')` 获取的第一个链接，其 `textContent` 包含标题+播放量+点赞+时长全部文本
- **现象**：中文标题无空格，第一个空格出现在播放量数字前，但标题本身含数字（如"4步"、"2026"）
- **结果**：`views` 字段会包含标题中的数字，如 views="82025516" 实际是标题中"4" + 播放量"8" + 点赞"2" + 时长"02:55:16"
- **✅ 解决方案**：使用 `a[href*="/video/BV"]` 遍历法（见上面"最佳提取方法"），该链接的 textContent 是 `"稍后再看N D HH:MM:SS"` 格式（N=播放量 D=弹幕），不包含标题文本

### 9. ⚠️ 绝对不能编造 BV ID（2026年5月15日实测）
- **问题**：当提取数据时缺少BV ID，LLM可能凭模式猜测BV号（如 `BV1Ek5q6gEX1` 到 `BV1Ek5q6gEX13`）
- **后果**：这些BV号指向的视频可能不存在或完全不相关，报告中的链接全部失效
- **⚠️ 规则：BV ID 必须从页面 DOM 中提取，绝不能靠模式推测或手动构造**
- **解决**：如果缺少BV数据，返回浏览器页面重新用 `a[href*="/video/BV"]` 提取真实ID

### 10. 滚动后 DOM 遍历 scope 膨胀（2026年5月15日实测）
- **问题**：初始页面中 `h3 → parentElement × 2-4` 能正确圈定单个视频卡片范围；但滚动后，DOM 结构变化导致同样的向上遍历层级会覆盖多个卡片甚至整个列表容器
- **现象**：所有视频的 author 字段变成同一个值（如全部显示 "小狐酱酱"）
- **原因**：B站懒加载后视频卡片的 DOM 嵌套深度改变，固定的向上遍历层级不再对应单个卡片
- **✅ 解决**：不要依赖 `parentElement × N` 向上遍历；改为用初始快照的作者/日期数据 + `a[href*="/video/BV"]` 提取的BV+播放量，在 Python 中按 BV 关联

### 11. 链接文本解析：播放量 vs 弹幕数的空格分隔（2026年5月15日确认）
- **DOM格式更新**：链接文本实际为 `"稍后再看VV DD HH:MM:SS"` — V=播放量, D=弹幕数, 然后是时长
- **示例**：`"稍后再看67 15 03:23:15"` → 播放量=67, 弹幕=15, 时长=03:23:15
- **⚠️ 之前的解析器把 "67 15" 连起来解析为 6715**，必须在解析播放量时只取第一个空格前的数字
- **已修复**：`bilibili_processor.py` 中的 `parse_views_and_duration()` 现在用 `split()` 取第一个 token

## 📁 参考实现

`references/bilibili_processor.py` — 完整的Python处理器，包含：
- `parse_views_and_duration()`: 处理粘连的播放量+时长字段（`"1.3万250932"` → views + duration）
- `parse_bilibili_date()`: 相对日期解析（昨天、前天、MM-DD、YYYY-MM-DD）
- `parse_video_data()`: 批量处理原始数据，返回含评分/duration/是否短视频字段的结构化列表
- `calc_score()`: 综合评分公式（播放量对数 + 新鲜度，无点赞数据时互动率为0）
- `sort_and_classify()`: 按score降序，返回长视频/短视频分组

**推荐做法**：将上述 `parse_video_data()`, `parse_bilibili_date()`, `parse_views_and_duration()`, `calc_score()`, `filter_recent()`, `sort_and_classify()` 复制到 `execute_code` 中直接运行，browser_console 只负责提取原始文本。
