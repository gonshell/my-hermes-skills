# 飞书文档映射（2026-05-30 实测）

## 当前文档映射（4个独立文档，无共享冲突）

| 任务 | Job ID | 飞书文档 Token | 文档链接 | 文档标题 |
|------|--------|--------------|---------|------|
| YouTube AI 热门（早 06:00） | `fa294bf7d232` | `EbHDdKARYo4vEExQiNGc3qiGnSe` | https://zt854jxlft.feishu.cn/docx/EbHDdKARYo4vEExQiNGc3qiGnSe | YouTube AI热门视频 · 早间档 |
| YouTube AI 热门（晚 20:00） | `d470b5d9b593` | `HhyMdusqdoVcW9xLyd2c2Yc2nnf` | https://zt854jxlft.feishu.cn/docx/HhyMdusqdoVcW9xLyd2c2Yc2nnf | YouTube AI热门视频 · 晚间档 |
| Bilibili AI 热门（21:00） | `1f4c7fb989aa` | `Virbd3YyBoYK9XxqaZOccEGRnio` | https://zt854jxlft.feishu.cn/docx/Virbd3YyBoYK9XxqaZOccEGRnio | Bilibili AI热门推送 · 晚间档 |
| Bilibili 全站热门（22:00） | `0e9f3cb36fe6` | `TcjbdsX0ToprvCxXPbQcbLqknTq` | https://zt854jxlft.feishu.cn/docx/TcjbdsX0ToprvCxXPbQcbLqknTq | Bilibili 全站热门推送 · 晚间档 |

> ✅ **每个任务独立文档**，彻底消除 overwrite 覆盖冲突。
> ❌ **旧文档已弃用**：`OoxcdJ72worwMHxwK73ctbdhn0b`（YouTube 旧合并）、`MjT6dT3abopHBpxkwPCcauGWn6e`（Bilibili 旧合并）

## 文档结构要求（h1/h2 标准标签）

```xml
<title>{文档标题}</title>
<h1>每日{平台} AI热门推送 · {日期} · {早间档/晚间档}</h1>
<h2>最热门长视频 TOP 15</h2>
<ol>...</ol>
<h2>最热门小视频 TOP 7</h2>
<ol>...</ol>
```

飞书目录**仅从 `h1`/`h2` 生成**，不用其他标签。`h1` 显示任务+日期+档期，`h2` 显示内容分类。

## 所有权转移

飞书文档创建后立即转移所有权给用户：

```bash
lark-cli drive transfer-owner \
  --file-token "<doc_id>" \
  --member-id "ou_a0b6be7e404317f09b2ec6df33bde74b" \
  --member-type openid
```

## 飞书文档操作命令

### 修改标题
```bash
lark-cli drive files patch \
  --params '{"file_token":"<doc_id>","type":"docx"}' \
  --data '{"new_title":"新标题"}'
```

### 删除文档
```bash
lark-cli drive +delete --file-token "<doc_id>" --type docx --yes
```

### 写入内容
```bash
# 从 HERMES_HOME（/Users/xiesg/）用相对路径
lark-cli docs +update --api-version v2 \
  --doc "<doc_id>" \
  --command overwrite \
  --content @./.hermes/hermes-agent/{filename}.xml \
  --doc-format xml
```

## 路径约束

`lark-cli --content @filepath` 必须从 HERMES_HOME（`/Users/xiesg/`）用**相对路径**：
- ✅ `--content @./.hermes/hermes-agent/bilibili-ai-content.xml`
- ❌ `--content @/absolute/path`（unsafe file path 报错）
- ❌ `--content @~/path`（无效）

## cronjob Python 路径展开问题

> ⚠️ `os.path.expanduser("~/.hermes/cron/output/")` 在 cronjob Python 进程中展开为 `/Users/xiesg/.hermes/home/.hermes/cron/output/`（错误路径）。

**解法：硬编码绝对路径**：
```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
xml_path = output_dir + f"youtube-ai-am_{date}.xml"
```

**lark-cli 读取 cron output 文件的正确路径**：
- ✅ `@./.hermes/cron/output/youtube-ai-pm_2026-06-08.xml`（从 HERMES_HOME 相对路径）
- ❌ `@./.hermes/hermes-agent/file.xml`（HERMES_AGENT_CWD，错误）
