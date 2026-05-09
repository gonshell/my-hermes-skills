# Enterprise / SaaS AI Agent Landscape

Research notes from investigating commercial and enterprise-facing AI agent solutions as of May 2026.

## Hermes Agent (Nous Research)

**Website:** https://hermes-agent.nousresearch.com  
**GitHub:** https://github.com/NousResearch/hermes-agent  
**License:** MIT (fully open source)

**Enterprise status:**
- No dedicated `/enterprise` or `/pricing` page (both 404 at time of research)
- No commercial/saas hosted tier — fully self-hosted only
- Nous Portal (https://portal.nousresearch.com) is an API portal but not an enterprise agent product
- For enterprise features (SSO, audit logs, team RBAC, support SLAs), contact Nous Research directly

**Key differentiators:**
- Self-improving skills + persistent memory
- Multi-platform gateway (Telegram, Discord, Slack, WhatsApp, etc.)
- Sandboxing: Docker, SSH, Singularity, Modal
- Fully provider-agnostic (OpenRouter, Anthropic, OpenAI, DeepSeek, local, 20+)
- Profiles for isolated multi-instance deployments

---

## Wegent (wecode.ai)

**Website:** https://wecode.ai  
**GitHub:** https://github.com/wecode-ai/Wegent  
**License:** Apache-2.0  
**Stars:** 553 · **Commits:** 1,504 · **Forks:** 94 (as of May 2026)

"AI-native operating system to define, organize, and run intelligent agent teams."

**Key features:**
- Multi-agent orchestration and team coordination
- GitLab, Jira, DingTalk integrations
- Browser power extension
- Active development (last commit May 8, 2026)
- Has an Enterprise page at `/enterprise` (currently returns empty/loading page — in development)

**Competitive position:** Similar category to Hermes Agent but focused on agent *teams* rather than single agent. May have commercial enterprise offerings in development.

---

## Open Claw

**GitHub:** https://github.com/wecode-ai/openclaw-weibo (Apache-2.0, 36 stars)

Not a standalone commercial product. The `openclaw-weibo` repo is a Weibo API integration. No separate Open Claw enterprise brand found.

---

## Competitive Summary

| | Hermes Agent | Wegent | Claude Code | Codex |
|---|---|---|---|---|
| **License** | MIT | Apache-2.0 | Proprietary | Proprietary |
| **Self-hosted** | ✅ | ✅ | ❌ | ❌ |
| **Multi-agent teams** | Via subagents | ✅ Native | ❌ | ❌ |
| **Enterprise/paid tier** | Contact Nous | Contact wecode.ai | ✅ Team | ✅ Enterprise |
| **SSO/RBAC** | No (self-host) | TBD | ✅ | ✅ |
| **Active development** | ✅ | ✅ | ✅ | ✅ |

---

## Recommendations for Enterprise Buyers

1. **Hermes Agent** — best for teams that want full control, self-host, and value the self-improving skills + multi-platform gateway. Reach out to Nous Research for commercial support SLAs.

2. **Wegent** — best for teams needing coordinated multi-agent workflows with existing devtool integrations (GitLab/Jira). Watch for enterprise product announcements from wecode.ai.

3. **Claude Code / Codex** — best for organizations wanting managed saas with enterprise support, SSO, and team management already built in. Trade-off: vendor lock-in, not self-hosted.

4. **Build on Hermes + extend** — fastest path to an enterprise internal agent system: self-host Hermes Agent, add MCP servers for your internal tools, use profiles for team isolation.

---

## Verified URLs (May 2026)

- Hermes Agent home: https://hermes-agent.nousresearch.com
- Hermes Agent docs: https://hermes-agent.nousresearch.com/docs
- Hermes GitHub: https://github.com/NousResearch/hermes-agent
- Nous Portal: https://portal.nousresearch.com
- Wegent GitHub: https://github.com/wecode-ai/Wegent
- wecode.ai home: https://wecode.ai (currently minimal/landing only)