---
name: session-state-verification
version: 1.0.0
description: "Verify ground truth on disk / via tool calls BEFORE reporting task status — never trust your own previous in-session self-description. Use when (1) the user asks to 'continue unfinished work' from a prior session, (2) a previous turn in the same session claimed a task was in-progress and the user asks for an update, (3) reporting deliverable status after a multi-step creation pipeline (write file → import to Feishu / Notion / etc.), (4) any case where my prior message said 'X is being worked on' or 'X is unfinished' but real disk/network state could disagree."
metadata:
  triggers:
    - "继续未完成的工作"
    - "请检查本轮对话，哪里未完成"
    - "刚才写到哪了"
    - "继续之前未完成的工作"
    - "上次的PRD/报告/方案写到哪了"
---

# Session State Verification

> **Core principle:** Your previous assistant message is a *claim*, not a fact. Always re-verify ground truth before reporting status to the user.

## Why this skill exists

I have a documented failure mode: after a multi-step deliverable pipeline (write long file locally → import to cloud → report), I will sometimes **reuse my in-progress status message** ("⏳正在写第一部分") in a later turn without re-checking whether the work actually completed. This creates two distinct false reports:

1. **False unfinished** — "X is not done yet" when X is actually 100% complete on disk and only the upload step is missing.
2. **False finished** — the mirror case after I claim "done" without re-verifying (rarer, same root cause).

The user's complaint is always the same shape: "你之前说还在写，但其实早就写完了。" The cost is trust — every subsequent status claim becomes suspect.

## The rule

**Before reporting "X is complete", "X is unfinished", or "X is in progress", verify ground truth.**

The verification step depends on the artifact type:

| Artifact type | Verification command |
|---------------|---------------------|
| Local file | `ls -la <path>` or `stat <path>` to confirm existence + size |
| Document content | `wc -c <path>` + check for required sections (e.g. `<h1>` count) |
| Feishu doc | Confirm `document_id` from the most recent `lark-cli docs +create` response |
| Multi-file pipeline | List output dir + check each expected file's mtime |
| Database / external | Re-query (don't trust cached state from earlier turn) |

**Always verify the LAST step's actual completion, not the overall plan progress.** The plan may be 7 steps but the last step (upload) may be the only thing missing.

## Workflow when user says "继续之前未完成的工作"

1. **Don't trust the prior message.** Query the actual session log / disk state:
   ```bash
   # Read the prior session's last messages to see what was actually claimed + tool-called
   sqlite3 /Users/xiesg/.hermes/state.db "SELECT id, role, content FROM messages WHERE session_id='<prior_session_id>' ORDER BY id DESC LIMIT 10"
   ```
2. **For each "⏳ in progress" item in the prior turn, check disk reality** — does the file exist? Is the size plausible? Does it contain the sections that should be there?
3. **For each expected deliverable (e.g. Feishu doc), check the deliverable's existence** — `drive +search` or check the return value of the last `docs +create` call in the prior session.
4. **Report based on the verified matrix**, not based on the prior turn's checklist:
   ```
   True state:
   - ✅ Local file plan-b-v2.xml (62316 bytes, 7 sections)
   - ❌ Feishu upload (no document_id returned in prior session)
   
   Only remaining work: import to Feishu.
   ```

## Pitfalls

- **Don't reuse the prior turn's todo summary verbatim.** The todo state may not reflect the actual ground truth if a tool call landed after the summary was written (the prior message23580 case).
- **A tool result that landed but wasn't acknowledged** still counts as completed. The system note `[Your previous turn was interrupted before you could process the last tool result(s)]` is your cue: read the last 1-3 tool results from the prior session, don't skip them.
- **Size check beats content check for big files.** For a 60KB XML, `wc -c` is faster and just as informative as full content scan. Reserve content scan for files under ~10KB.
- **For multi-step pipelines, walk backward from the last step.** The last step is most likely where things got stuck, not the middle.

## Verification commands

```bash
# 1. List files in the working directory, sorted by mtime (newest last action)
ls -lt /Users/xiesg/workspace/<project>/

# 2. Confirm a specific deliverable exists with expected size
ls -la /Users/xiesg/workspace/<project>/<filename>
wc -l /Users/xiesg/workspace/<project>/<filename>

# 3. Read the actual last messages of a prior session
python3 -c "
import sqlite3
con = sqlite3.connect('/Users/xiesg/.hermes/state.db')
cur = con.cursor()
cur.execute('SELECT id, role, substr(content,1,200) FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 5', ('<session_id>',))
for r in cur.fetchall():
    print(r[0], r[1], r[2])
"

# 4. Check section count in a structured document (XML/Markdown)
python3 -c "
import re
with open('<path>') as f:
    c = f.read()
print(f'headers: {len(re.findall(r\"<h[12][^>]*>\", c))}')
print(f'bytes: {len(c)}')
"
```

## When NOT to apply

- Single-turn tasks where there's no prior turn to misalign with.
- Tasks where the deliverable's state IS your last tool result (you already have ground truth in the most recent tool output).
- User asks "what did you do" — that's asking for the narrative, not ground-truth status.

## Related

- This lesson pairs with the user preference: "继续未完成的工作时直接执行不解释" — once verification is done, don't write a long explanation, just do the remaining work and report the verified result.
- For multi-agent work, combine with `superpowers` skill if loaded — verify after each subagent's handoff, not just at the end.