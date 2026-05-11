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

```
# 3天内最热门长视频（按播放量）
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=click&duration=4

# 3天内最热门小视频
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=click&tids=124&duration=4

# 3天内最新发布长视频
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=pubdate&duration=4

# 3天内小视频最新发布
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20ChatGPT%20Claude%20Qwen%20Deepseek&order=pubdate&tids=124&duration=4
```

### B站时间筛选参数
- `duration=4` 表示3天内（实际为4天范围）
- 其他选项：duration=1(10分钟内)、duration=2(一天内)、duration=3(一周内)

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

### 1. duration=4 参数严重不可靠（重要！持续有效！）
- **问题**：`duration=4`（3天内）在 browser 环境下几乎总是返回2025年甚至更老的视频
- **原因**：B站搜索API的日期过滤在非登录态/headless环境下失效
- **状态**：2026年5月实测仍完全失效，无改善迹象
- **解决方案（实测有效）**：
  1. 使用 `duration=1`（10分钟内）+ 在搜索词中包含年月：`DeepSeek 2026年4月` 或 `AI 2026 5月`
  2. 使用 `order=pubdate&duration=1` 获取最新发布内容
  3. 在代码层面按实际日期过滤 freshness > 0（7天内）
  4. **最佳实践**：多次搜索组合——通用AI词+年月词 + 细分领域词+年月词
- **⚠️ 重要约束**：即使使用上述方法，在每月中期运行时"3天内"窗口非常狭窄（可能只有1-2条视频），因为4月中旬的日期（04-10、04-12等）在5月10日已超7天新鲜度窗口。**建议将cron job安排在月初运行**，或适当扩大评分算法的新鲜度衰减周期以包含更多内容。

```bash
# 实测有效的搜索URL模式（2026年5月仍有效）
# 最新发布（按时间，最有效）
https://search.bilibili.com/video?keyword=AI%20LLM%20GPT%20Claude%20Qwen%20Deepseek%202026%E5%B9%B4&order=pubdate&duration=1

# 最热门（按播放量）
https://search.bilibili.com/video?keyword=AI%20GPT%20Claude%20Qwen%20Deepseek%202026%E5%B9%B4&order=click&duration=1

# 细分领域+年月（补充）
https://search.bilibili.com/video?keyword=DeepSeek%20RAG%20Agent%202026%204%E6%9C%88&order=pubdate&duration=1
https://search.bilibili.com/video?keyword=AI%202026%204%E6%9C%88%E6%9C%80%E6%96%B0&order=pubdate&duration=1
```

### 2. 播放量 + 视频时长混合字段解析（2026年5月实测修正）
- **DOM格式**：`"1.3万250932"` 或 `"4万70721"` — 播放量、点赞数、时长三者粘连！
- **真实格式**：`"1.3万" + "25" + "09:32"` → 播放量=1.3万，时长=25:09:32
- **解析规则**：
  - 第一个空格前 = 播放量（可能是 `1.4万` 或 `4245`）
  - 时长格式为 `HHMMSS` 或 `MMDDSS`，没有分隔符直接拼接在播放量后面
  - **⚠️ 必须用正则提取时长**：`/(\d{1,2}):(\d{2}):(\d{2})$/` 或 `/(\d{1,2}):(\d{2})$/`
  - 时长如果出现 `25:09:32`（>24小时）或 `09:32`（分钟），说明是视频总时长
- **python解析实现**：
  ```python
  def parse_views_and_duration(text):
      """解析 '1.3万250932' → views=13000, duration='25:09:32'"""
      if not text: return 0, ''
      # 先匹配时长（倒序找 HH:MM:SS 或 MM:SS）
      m = re.search(r'(\d{1,2}):(\d{2}):(\d{2})\s*$', text)   # HH:MM:SS
      if m:
          h, mn, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
          duration = f"{h}:{mn:02d}:{s:02d}"
          num_part = text[:m.start()].strip()
      else:
          m2 = re.search(r'(\d{1,2}):(\d{2})\s*$', text)        # MM:SS
          if m2:
              mn, s = int(m2.group(1)), int(m2.group(2))
              duration = f"{mn}:{s:02d}"
              num_part = text[:m2.start()].strip()
          else:
              duration = ''
              num_part = text.strip()
      # 解析播放量
      num_part = re.sub(r'[^\d.万]', '', num_part)
      if '万' in num_part:
          views = float(num_part.replace('万','')) * 10000
      else:
          views = int(num_part) if num_part.isdigit() else 0
      return views, duration
  ```
- **重要**：时长 > 24h 意味着B站视频时长格式为 `HH:MM:SS`（可能超过24小时）

### 3. 日期解析（相对日期 → 实际日期）
Bilibili 搜索结果使用相对日期格式，必须转换：
| 显示格式 | 含义 | 转换结果（假设2026-04-27） |
|----------|------|--------------------------|
| `昨天` | 昨天 | 2026-04-26 |
| `3小时前` / `刚刚` | 几小时前 | 2026-04-27（当天） |
| `前天` | 前天 | 2026-04-25 |
| `04-20` | 月-日 | 2026-04-20（如月<=当前月则当年，否则去年） |

⚠️ **CRITICAL BUG FOUND**: `昨天` 和 `前天` 有时不会被作者的「·」分隔解析捕获，直接以原始字符串形式出现在date字段中！必须在提取后额外处理这些相对日期字符串。

```python
def parse_bilibili_date(date_str, current_date=datetime(2026, 4, 27)):
    if not date_str:
        return None, None
    date_str = date_str.strip()
    
    # 关键：先检查是否包含小时前/昨天/前天等相对日期
    if '小时前' in date_str or date_str == '刚刚':
        # 计算小时数
        if '小时前' in date_str:
            try:
                hours = int(re.search(r'(\d+)', date_str).group(1))
                pub_date = current_date - timedelta(hours=hours)
            except:
                pub_date = current_date
        else:
            pub_date = current_date
        return pub_date, pub_date.strftime('%m-%d')
    
    if date_str == '昨天':
        pub_date = current_date - timedelta(days=1)
        return pub_date, '昨天'
    elif date_str == '前天':
        pub_date = current_date - timedelta(days=2)
        return pub_date, '前天'
    elif '-' in date_str and len(date_str) == 5:  # MM-DD格式
        try:
            m, d = map(int, date_str.split('-'))
            # 如果月份大于当前月份，说明是今年；否则是去年（跨年问题）
            year = current_date.year if m <= current_date.month else current_date.year - 1
            pub_date = datetime(year, m, d)
            return pub_date, date_str
        except:
            return None, date_str
    elif '-' in date_str and len(date_str) == 10:  # YYYY-MM-DD格式
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

## 📁 参考实现

`references/bilibili_processor.py` — 完整的Python处理器，包含：
- `parse_views_and_duration()`: 处理粘连的播放量+时长字段（`"1.3万250932"` → views + duration）
- `parse_bilibili_date()`: 相对日期解析（昨天、前天、MM-DD、YYYY-MM-DD）
- `parse_video_data()`: 批量处理原始数据，返回含评分/duration/是否短视频字段的结构化列表
- `calc_score()`: 综合评分公式（播放量对数 + 新鲜度，无点赞数据时互动率为0）
- `sort_and_classify()`: 按score降序，返回长视频/短视频分组

推荐在 `execute_code` 中使用，browser_console 只负责提取原始文本。
