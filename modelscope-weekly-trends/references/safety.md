# 失败处理

## 边界条件

| 情况 | 处理 |
|---|---|
| 4 板块总条目 < 5 | 标"⚠️ 数据不足",仍发 |
| 飞书文档不存在 | 飞书 IM 告警,不创建 |
| 飞书追加后 re-fetch 长度没增加 | 重试一次 → 仍失败 → 告警 |
| 飞书 IM 失败 | 不重试,本地有输出 |
| 数据源全部失败 | 飞书 IM 告警,不发周报 |
| 本周已跑过 | 跳过 |

## 暂停

```bash
cronjob action='pause' job_id='modelscope-weekly-mon'
```

## 强制重跑

手动触发或删除 `state/config.json` 的 `last_week` 字段。

## 备份

`state/config.json` 含 doc_id,丢失后需重建。

## 防止目录误删

**事故案例**(2026-06-29):整个 `~/.hermes/skills/modelscope-weekly-trends/` 被误删。原因是脚本用 tempfile 写临时文件后清理时 cwd 或路径出错,`rm` 误伤了 skill 目录。

**预防措施**:
1. 每个子目录加 `.gitkeep` — `rm -rf` 看到非空目录会犹豫(但不能完全防)
2. 脚本里用 `tempfile.mktemp(dir='/tmp')` 而非 skill 目录下的路径
3. 不要在 skill 目录下执行任何 `rm` 命令
4. 定期备份: `cp -r ~/.hermes/skills/modelscope-weekly-trends/ ~/.hermes/backups/skill-$(date +%Y%m%d)/`
