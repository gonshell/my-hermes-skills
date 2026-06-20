# my-hermes-skills

Auto-synced mirror of `~/.hermes/skills/` (the user-installed Hermes skills collection).

This repo is updated nightly by a scheduled cron job that copies the live skills directory here and pushes to `main`.

## Layout

Each top-level folder is one Hermes skill (a `SKILL.md` plus optional `references/`, `templates/`, `scripts/`, `assets/`).

Skill categories include:

- **Productivity**: `lark-*`, `notion`, `pptx-generator`, `powerpoint`, `airtable`, `linear`, `nano-pdf`, `workspace-organization`, `editorial-multi-agent`, `document-content-workflow`, `teams-meeting-pipeline`, `reflect-then-confirm`
- **Dev / coding**: `github`, `agentic-development`, `superpowers`, `plan`, `simplify-code`, `test-driven-development`, `hermes-agent-skill-authoring`, `hiclaw`, `hermes-s6-container-supervision`
- **Data / ML**: `mlops/*`, `data-science/*`, `mlops/evaluation`, `mlops/inference`, `mlops/training`, `jupyter-live-kernel`, `pdf-to-qa-csv`, `aircraft-casting-expert`
- **Research / docs**: `arxiv`, `arxiv-to-wiki`, `llm-wiki`, `polymarket`, `blogwatcher`, `find-classical-cs-papers`, `ai-agent-research`, `feishu-content-analysis`, `tech-research-doc`, `nano-pdf`
- **Media / creative**: `creative/*` (ascii, manim, p5js, comfyui, etc.), `media/*` (gif, songsee, spotify, video-content-workflow), `frontend-design`, `popular-web-designs`, `sketch`, `pixel-art`, `ascii-video`, `manim-video`, `comfyui`, `songwriting-and-ai-music`, `baoyu-*`
- **Social / messaging**: `imessage`, `weibo-cli`, `xurl`, `email`, `agentmail`, `yuanbao`
- **Smart home / IoT**: `openhue`, `findmy`, `find-nearby`
- **Gaming**: `minecraft-modpack-server`, `pokemon-player`
- **Other utilities**: `humanizer-zh`, `humanizer`, `red-teaming/godmode`, `codebase-exploration`, `session-state-verification`, `mcp/native-mcp`, `mcp/mcporter`

## Notes

- Runtime metadata (`.usage.json`, `.archive/`, `.hub/`, `.curator_*`, `.bundled_manifest`) is **not** synced — see `.gitignore`.
- Python virtualenvs (`.venv/`) inside skill sub-projects are excluded.
- Updated nightly by a cron job — manual edits here will be overwritten on the next sync.
