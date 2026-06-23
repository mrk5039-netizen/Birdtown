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

## Wiring in real integrations

The environment this was built for exposes ZoomInfo, Gmail, Google Calendar,
Slack, and Notion as MCP tools. The code ships with deterministic local stubs
so it runs without accounts; each is marked `# INTEGRATION:` in `tools.py` with
the exact MCP tool to call:

| Step              | Stub returns        | Swap in (MCP)                                              |
| ----------------- | ------------------- | --------------------------------------------------------- |
| `research_account`| placeholder profile | `mcp__ZoomInfo__account_research`, `enrich_companies`, `search_intent` |
| `queue_outreach_email` | local draft    | `mcp__Gmail__create_draft`                                |
| `propose_meeting` | booking link only   | `mcp__Google_Calendar__suggest_time` + `create_event`     |
| `log_lead`        | `data/crm.jsonl`    | `mcp__Slack__slack_send_message`, `mcp__Notion__notion-create-pages` |

## Project layout

```
sales-agent/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
└── concentric_sdr/
    ├── agent.py             # system prompt + tool-runner loop
    ├── tools.py             # research / qualify / email / meeting / CRM tools
    ├── product.py           # Concentric product & ICP knowledge base
    └── config.py            # model + settings
```

## Responsible use

This agent is for **legitimate B2B sales development only**. Respect GDPR,
CAN-SPAM, and CCPA: business context, honest subject lines, easy opt-out, and a
real reason for every message. Do not use it for bulk scraping or unsolicited
mass outreach.
