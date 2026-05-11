# AI Agent Protocol — Authoritative Sources

> Verification methodology and authoritative sources for AI agent protocol research. Updated May 2026.

## MCP (Model Context Protocol)

**Official spec**: https://modelcontextprotocol.io/specification/2025-11-25
**GitHub**: https://github.com/modelcontextprotocol/specification (8.1k stars, 3931 commits)
**Version**: 2025-11-25 (latest as of May 2026)

Key sections:
- Architecture: Host → Client → Server (one host, multiple clients)
- Transports: **Streamable HTTP** (replaces deprecated HTTP+SSE) + stdio
- Base: JSON-RPC 2.0, capability negotiation at init
- Server features: Resources, Prompts, Tools
- Client features: Roots, Sampling, Elicitation
- stdio: subprocess stdin/stdout; one request → one response (sync); notifications (no id) for server→client push
- Session management for resumability

Verified correct in research doc.

## A2A (Agent-to-Agent Protocol)

**Org**: https://github.com/a2aproject (NOT Anthropic)
**Go SDK**: https://github.com/a2aproject/a2a-go (369 stars, active)
**Version**: v0.3.0 (see openclaw-a2a-gateway description)

⚠️ **Attribution correction**: A2A is maintained by **a2aproject** org, NOT Anthropic. The `a2a.antropic.com` domain had cert issues. Anthropic's involvement is unconfirmed — do not attribute A2A to Anthropic without verification.

Key files in a2a-go:
- `a2a/agent.go` — Agent definition
- `a2a/push.go` — Push notifications
- `a2a/svcparams.go` — Service parameters
- `.agent/workflows/` — Agent workflow definitions

Other A2A repos:
- `win4r/openclaw-a2a-gateway`: OpenClaw plugin implementing A2A v0.3.0 (484 stars)

## ACP (Agent Client Protocol)

**Origin**: Defined by **Zed Industries** (zed.dev), not Hermes or Nous Research.
**Python SDK**: `pip install agent-client-protocol` (PyPI: agent-client-protocol, by Zed Industries)
**SDK repo**: https://github.com/agentclientprotocol/python-sdk
**Docs**: https://agentclientprotocol.github.io/python-sdk/
**Version**: 0.10.0 (latest as of May 2026)

**What it is** (from official docs):
> "ACP is the stdio protocol that lets 'clients' (editors, shells, CLIs) orchestrate AI 'agents.' Sessions exchange structured payloads."

**Hermes's role**: Consumer/implementer. Hermes's `acp_adapter/` directory implements the ACP SDK's `acp.run_agent()` interface, acting as an ACP server. The `agent-client-protocol` package is listed as a dependency in `pyproject.toml` under the `acp` extra.

**Attribution**: Do NOT attribute ACP to Nous Research or claim it is Hermes-proprietary. ACP belongs to Zed Industries. Hermes is one of several projects (alongside OpenClaw's A2A gateway) that adopted the protocol.

## Function Calling

**OpenAI**: https://platform.openai.com/docs/guides/function-calling
- `arguments` field is JSON string (must `JSON.parse`)
- API-level enforcement (not prompt-based)

**Claude**: Tool Use via prompt引导 (NOT API enforcement)
- Model outputs XML-like tags; system extracts via regex
- Tag format may have changed — verify against current docs if implementing

## Skills (Agent Skills)

**Reference**: https://modelcontextprotocol.io/docs/develop/build-with-agent-skills
- `mcp-server-dev` plugin: `build-mcp-server`, `build-mcp-app`, `build-mcpb`
- Format: SKILL.md + references/ + templates/ + scripts/
- Dynamic discovery (no restart needed)

## Verification Checklist

When writing about a protocol, confirm:
- [ ] Official spec URL exists and is accessible
- [ ] GitHub repo with actual code (not justarketing)
- [ ] Version/tag visible
- [ ] Attribution (who maintains it) confirmed
- [ ] Implementation count (SDKs, languages)
- [ ] If no authoritative source found → say "unconfirmed" not "fact"
