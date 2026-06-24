# Source Accessibility by Company (snapshot 2026-06-23)

Tested from Hermes sandbox on macOS 13.7.8, no proxy, no login. Path viability: ✅ works, ⚠ partial, ❌ blocked.

## Tier-1: Always works (no auth)

| Source | Path | Note |
|---|---|---|
| GitHub raw | `https://raw.githubusercontent.com/<repo>/<branch>/<path>` | Best signal for community-maintained landscape. |
| SearXNG public | `mcp_websearch_searxng_searxng_web_search` | Good for Chinese + English blog/article indexing. |
| 小宇宙 (xiaoyuzhou.fm) | podcast transcript pages | Long interviews with product leads; full text indexable. |
| 知乎 (zhihu.com) | 全文 (需未登录) | Worker anonymous sharing, medium timeliness. |
| 掘金 / CSDN / InfoQ | 全文 (需未登录) | Engineer跳槽分享, occasional real JD screenshots. |
| 百度百科 / 维基百科 | 公开 | Org history, leadership names. |
| 公司官方产品页 | 官网 (非 careers) | Team / product info, no JD. |
| 微信公众号 (通过搜狗) | web.wechat / 搜狗微信 | Long articles, sometimes full JD screenshots. |

## Tier-2: Works for some, not others

| Source | Path | Note |
|---|---|---|
| LinkedIn (international) | public posts | Works for DeepSeek, Moonshot, Zhipu, MiniMax posts; blocked in CN. |
| 公司官方 "careers" 入口 | first page | Often just shows login CTA, list behind JS. |
| MoKa / ShowMoka portals | curl from sandbox | **Redirect loop** for most tenants; can't enumerate. |
| GreesnShrpoon / BossMoke clones | varies | Mostly blocked. |
| Boss直聘 (zhipin.com) | some Google cache hits | **Slider captcha** if you try to load full page. |
| 拉勾 (lagou.com) | Cloudflare | **Blocked** at IP level. |

## Tier-3: Always blocked (no auth in sandbox)

| Source | Why blocked |
|---|---|
| Boss直聘 JD 详情页 | Slider + 登录 |
| 拉勾 JD 详情页 | Cloudflare 5s challenge |
| 猎聘 JD 详情页 | Login wall |
| 脉脉 JD 详情页 | Login wall + mobile-only |
| 字节 jobs.bytedance.com JD list | JS SPA, 列表 needs login |
| 阿里 / 腾讯 / 百度 careers JD list | JS SPA + login |
| 智谱 zhipuai.cn 加入我们 (internal list) | Moka redirect loop |
| LinkedIn JD details (some) | "Sign in to view" for some posts |

## Working pattern

```
SearXNG (多关键词) → GitHub raw (社区指南) → 小宇宙/知乎/掘金 → 公司产品页 → LinkedIn 国际站
```

If all 5 give no JD: that's still a real answer ("No public JD exists for X role at Y company as of 2026-06-23"). Report it with the path-trail, do NOT redirect to "you need to apply".

## When user offers to provide login

Boss/拉勾/猎聘/Moka 都可以接受用户提供的 login cookie via `curl -H "Cookie: ..."` header. **Always ask user to confirm before doing this** — they own the credentials.
