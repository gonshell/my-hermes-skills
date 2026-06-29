# 飞书文档协议(纯 Markdown)

## 文档元数据

- **标题**:`魔搭社区 · 周度趋势速览`
- **所有者**:用户 (`ou_a0b6be7e404317f09b2ec6df33bde74b`)
- **权限**:可读(用户)+ 可写(hermes bot)

## 追加方式

**只用 `docs +update --mode append`**,不传图片。

```bash
cd <md 文件所在目录>
lark-cli docs +update --doc <doc_id> --mode append --markdown "@./weekly_Wxx.md"
```

**重要**: `--markdown @./xxx.md` 路径必须是 CWD 相对路径。

## 写后必读验证

每次追加后必须 re-fetch,确认内容长度增加:

```bash
lark-cli docs +fetch --doc <doc_id> 2>/dev/null | python3 -c "
import json,sys
d = json.loads(sys.stdin.read())
md = d['data']['markdown']
print(f'长度:{len(md)}')
"
```

如果长度没有增加 → 重试一次 → 仍失败 → 飞书 IM 告警。

## 文档结构

```markdown
# 魔搭社区 · 周度趋势速览
> 由 modelscope-weekly-trends skill 自动生成 · 每周一/三/六追加
> 归档规则:每周一节,最新在文档末尾

---

## 2026-W26 周一快照(2026-06-23 ~ 2026-06-29)

### TL;DR
...

### 16 格速览
| 关注点 | 模型 | 数据 | 工具 | 论文 |
|---|---|---|---|---|
| 新增 | ... | ... | ... | ... |
| 趋势 | ... | ... | ... | ... |
| 反常 | ... | ... | ... | ... |
| 钩子 | ... | ... | ... | ... |

### 关键数据
...

### 反常详细分析
...

### 下周重点
...

### 跨周追踪
...

---

## 2026-W26 周三更新(2026-06-25)
...

---

## 2026-W25 周一快照(...)
...
```

## overwrite 场景

只在"文档内容出问题需要重置"时用 `--mode overwrite`,正常运行只用 `--mode append`。

## doc_id

当前:`DqQ6daptXoSRzKxUvjRcMCasnng`
URL:`https://www.feishu.cn/docx/DqQ6daptXoSRzKxUvjRcMCasnng`
持久化:`state/config.json`
