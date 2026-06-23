# Concentric SDR — Autonomous AI Sales Agent

An autonomous **Sales Development Representative (SDR)** for
[Concentric AI](https://concentric.com), the agentic Data Security Posture
Management (DSPM) platform.

It works a prospect the way a strong human SDR does:

1. **Research** the target account (firmographics, tech, buying triggers).
2. **Qualify** it against Concentric's ideal customer profile and score the fit.
3. **Personalize** one tailored cold email for the right buyer persona.
4. **Act** — queue the email and propose a meeting (with a self-serve booking link).
5. **Record** the lead and next step to the CRM (and optionally Slack).

It's built on the **Anthropic SDK** using `claude-opus-4-8` with adaptive
thinking and the beta **tool runner**, which drives the
research → qualify → write → act loop automatically.

## Why it's grounded and safe

- **No hallucinated claims.** The agent quotes only from a curated product
  knowledge base (`product.py`) and enriched research. It's instructed to
  confirm, not guess, any firmographic it doesn't have.
- **Human-in-the-loop by default.** `SDR_DRY_RUN=true` (the default) means the
  agent only *drafts* emails and *proposes* meetings — nothing is sent until a
  human approves. Drafts land in `data/outbox/`.
- **Compliance checks in code.** `queue_outreach_email` rejects deceptive
  subject lines, over-long bodies, and missing opt-outs — and the agent must
  revise and resubmit.
- **One prospect at a time.** No bulk blasting — every message is personalized.

## Setup

```bash
cd sales-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
```

## Usage

```bash
# Work a prospect end-to-end
python main.py --domain acme.com --persona CISO

# Free-form task
python main.py "Research finserv-co.com and draft outreach to their Head of Data Security"

# Interactive
python main.py --interactive
```

By default everything runs in **dry-run**: review the drafts in `data/outbox/`
and the pipeline in `data/crm.jsonl`. Add `--live` only with authorization.

## Wiring in real integrations (live MCP)

The agent runs on **two tool layers**:

- **Local tools** (`tools.py`) — the policy brain: ICP scoring, the outreach
  compliance gate, and CRM bookkeeping run in code we control.
- **Remote MCP servers** (`integrations.py`) — the real I/O: ZoomInfo, Gmail,
  Google Calendar, and Slack are reached through Anthropic's `mcp_servers`
  connector, so Claude calls their tools directly and the provider executes
  them server-side.

To go live, list your MCP servers in a JSON file and point `SDR_MCP_CONFIG` at it:

```bash
cp mcp_servers.example.json mcp_servers.json   # edit URLs to your real endpoints
export SDR_MCP_CONFIG=$PWD/mcp_servers.json
export ZOOMINFO_MCP_TOKEN=... GMAIL_MCP_TOKEN=...   # tokens stay in env, not the file
```

When servers are connected the agent automatically uses them, keeping the local
layer as the gate:

| Step              | Local (always) | Live MCP tool                                  |
| ----------------- | -------------- | ---------------------------------------------- |
| Research          | `score_lead`   | ZoomInfo `account_research`, `enrich_companies`, `search_intent` |
| Outreach          | `queue_outreach_email` (compliance gate) | Gmail `create_draft` (after the gate passes) |
| Meetings          | `propose_meeting` | Google Calendar `suggest_time` + `create_event` |
| Logging           | `log_lead` → `data/crm.jsonl` | Slack `slack_send_message`           |

With no `SDR_MCP_CONFIG` set, the agent runs purely on local stubs — the safe
default for development.

## Project layout

```
sales-agent/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
├── mcp_servers.example.json # live integration config template
└── concentric_sdr/
    ├── agent.py             # system prompt + tool-runner loop
    ├── tools.py             # local tools: qualify / email gate / meeting / CRM
    ├── integrations.py      # remote MCP connector wiring (ZoomInfo/Gmail/...)
    ├── product.py           # Concentric product & ICP knowledge base
    └── config.py            # model + settings
```

## Responsible use

This agent is for **legitimate B2B sales development only**. Respect GDPR,
CAN-SPAM, and CCPA: business context, honest subject lines, easy opt-out, and a
real reason for every message. Do not use it for bulk scraping or unsolicited
mass outreach.
