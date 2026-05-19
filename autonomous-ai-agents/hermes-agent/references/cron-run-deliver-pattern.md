# Cron Job Run + Observe Pattern

## Problem

`cronjob(action='run', job_id=xxx)` triggers a job immediately, but when the job's `deliver` is set to `local`, the execution output is **silently discarded** — you get a success confirmation with no actual output.

This is confusing when you want to observe a manual trigger's full execution log.

## Solution

Temporarily flip `deliver` to `origin` before running, then restore it:

```python
# 1. Change deliver to 'origin' (current chat)
cronjob(action='update', job_id='xxx', deliver='origin')

# 2. Trigger the run
cronjob(action='run', job_id='xxx')

# 3. Restore deliver to 'local'
cronjob(action='update', job_id='xxx', deliver='local')
```

## Why This Happens

`deliver` controls where cron output goes when the job fires. `local` = save only (no push to any channel). Manual `run` inherits this setting — it does not override it.

## Alternative

If the job's script produces a visible side-effect (e.g., pushes a Git commit, writes a file), you can observe the effect directly instead of capturing stdout. This is what the skills-sync job does — it makes git commits and file changes that are independently verifiable.

## When to Use

- Debugging a cron job that works in your head but fails in practice
- Verifying a new job before relying on it
- Comparing two runs with different parameters

When not to use: if the job's effects are externally observable (git push, file write, message sent), prefer observing the effect over capturing stdout.
