"""Tools the Concentric SDR agent can call.

Design principle (see Anthropic's agent-design guidance): the *model* writes
the prospect research synthesis and email copy in its reasoning; these tools
are the **side-effecting, gated actions**. Each action that touches the outside
world (sending mail, booking time, writing to the CRM) is a dedicated tool so
the harness can validate it, gate it behind dry-run, and audit it.

Each tool is decorated with `@beta_tool`, so the Anthropic SDK generates the
JSON schema from the type hints + docstring automatically and the tool runner
executes them in the agentic loop.

The integration points (ZoomInfo, Gmail, Calendar, Slack) are stubbed with
deterministic local behavior so the agent runs end-to-end without external
accounts. Each stub is marked `# INTEGRATION:` where you wire in the real MCP
tool call.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from anthropic import beta_tool

from .config import Settings
from . import product

# Local artifact stores so the agent's actions are observable end-to-end.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_OUTBOX = _DATA_DIR / "outbox"
_CRM = _DATA_DIR / "crm.jsonl"

# Settings is process-global; set once at startup by agent.py.
_SETTINGS = Settings()


def configure(settings: Settings) -> None:
    """Inject operator settings before the agent runs."""
    global _SETTINGS
    _SETTINGS = settings
    _OUTBOX.mkdir(parents=True, exist_ok=True)
    _CRM.parent.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Research
# --------------------------------------------------------------------------- #
@beta_tool
def research_account(domain: str) -> str:
    """Research a target company by its web domain to inform outreach.

    Returns firmographics, likely tech stack, recent buying-trigger signals,
    and the most relevant buyer personas. Call this first for any new prospect.

    Args:
        domain: The company's primary web domain, e.g. "acme.com".
    """
    domain = domain.strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]

    # INTEGRATION: replace this block with a real lookup, e.g.
    #   mcp__ZoomInfo__account_research / enrich_companies / enrich_news
    #   mcp__ZoomInfo__search_intent (for active data-security intent topics)
    # and map the response into the dict below. The deterministic stub lets the
    # agent reason about a realistic shape without an account.
    profile = {
        "domain": domain,
        "company_name": domain.split(".")[0].title(),
        "employee_estimate": "unknown — enrich via ZoomInfo before quoting",
        "industry": "unknown — enrich before quoting",
        "tech_signals": [
            "Microsoft 365 / Google Workspace (verify)",
            "Cloud data stores: AWS/Azure/Snowflake (verify)",
        ],
        "possible_triggers": product.IDEAL_CUSTOMER_PROFILE["triggers"],
        "relevant_personas": product.IDEAL_CUSTOMER_PROFILE["buyer_titles"],
        "note": (
            "This is a stub profile. Enrich with ZoomInfo before making any "
            "specific firmographic claim in outreach. Do not invent numbers."
        ),
    }
    return json.dumps(profile, indent=2)


# --------------------------------------------------------------------------- #
# Qualification
# --------------------------------------------------------------------------- #
@beta_tool
def score_lead(
    employee_count: int,
    industry: str,
    persona_title: str,
    active_triggers: str = "",
) -> str:
    """Score a lead's fit against Concentric's ideal customer profile (ICP).

    Returns a 0-100 fit score, a tier (A/B/C/disqualified), and a rationale.
    Use this before deciding whether (and how hard) to pursue a prospect.

    Args:
        employee_count: Approximate number of employees.
        industry: The company's industry, e.g. "financial services".
        persona_title: The target contact's job title.
        active_triggers: Comma-separated buying signals observed, if any.
    """
    score = 0
    reasons: list[str] = []

    # Size: Concentric is strongest upmarket.
    if employee_count >= 1000:
        score += 40
        reasons.append("Enterprise size (1,000+) — core ICP.")
    elif employee_count >= 500:
        score += 28
        reasons.append("Mid-market (500-999) — solid fit.")
    elif employee_count >= 200:
        score += 12
        reasons.append("Smaller (200-499) — fit possible but not ideal.")
    else:
        reasons.append("Below 200 employees — typically below ICP.")

    # Industry fit.
    icp_industries = [i.lower() for i in product.IDEAL_CUSTOMER_PROFILE["industries"]]
    if any(i in industry.lower() for i in icp_industries):
        score += 25
        reasons.append(f"Industry '{industry}' is a target vertical.")
    else:
        score += 5
        reasons.append(f"Industry '{industry}' is outside core verticals.")

    # Persona fit.
    persona_l = persona_title.lower()
    if any(k in persona_l for k in ["ciso", "security", "data protection", "compliance", "grc", "privacy"]):
        score += 25
        reasons.append("Title maps to a data-security/compliance buyer.")
    elif any(k in persona_l for k in ["cio", "cto", "it", "engineering", "infrastructure"]):
        score += 12
        reasons.append("Adjacent technical buyer — influencer, not economic buyer.")
    else:
        reasons.append("Title is not an obvious data-security buyer.")

    # Triggers add urgency.
    trigger_count = len([t for t in active_triggers.split(",") if t.strip()])
    if trigger_count:
        bonus = min(10, trigger_count * 5)
        score += bonus
        reasons.append(f"{trigger_count} active buying trigger(s) (+{bonus}).")

    score = min(score, 100)
    if score >= 70:
        tier = "A"
    elif score >= 50:
        tier = "B"
    elif score >= 30:
        tier = "C"
    else:
        tier = "disqualified"

    return json.dumps(
        {"score": score, "tier": tier, "rationale": reasons},
        indent=2,
    )


# --------------------------------------------------------------------------- #
# Outreach (gated)
# --------------------------------------------------------------------------- #
_BANNED_SUBJECT_PATTERNS = [
    r"^\s*re:",          # fake reply
    r"^\s*fwd?:",        # fake forward (fw: / fwd:)
    r"!!!",              # spammy punctuation
    r"\bfree\b.*\bnow\b",
]


def _validate_outreach(subject: str, body: str) -> list[str]:
    """Return a list of compliance problems; empty means it passed."""
    problems: list[str] = []
    s = subject.lower()
    for pat in _BANNED_SUBJECT_PATTERNS:
        if re.search(pat, s):
            problems.append(f"Subject line looks deceptive/spammy (matched /{pat}/).")
    if len(body.split()) > 200:
        problems.append("Body is too long for a cold email (>200 words). Tighten it.")
    if "unsubscribe" not in body.lower() and "opt out" not in body.lower() and "reply" not in body.lower():
        problems.append("No clear opt-out / reply path. Add one.")
    return problems


@beta_tool
def queue_outreach_email(to_email: str, subject: str, body: str, persona: str = "") -> str:
    """Queue a *personalized* cold outreach email to a single prospect.

    The email is validated for compliance, then either saved as a draft for
    human approval (dry-run, the default) or handed to the mail integration.
    Never use this to send identical bulk messages — one prospect at a time,
    each personalized.

    Args:
        to_email: The prospect's email address.
        subject: Subject line — clear and honest, no "Re:"/"Fwd:" tricks.
        body: Plain-text email body, under ~200 words, with an easy opt-out.
        persona: The buyer persona this is written for (e.g. "CISO").
    """
    problems = _validate_outreach(subject, body)
    if problems:
        return json.dumps(
            {"status": "rejected", "reasons": problems,
             "instruction": "Revise the email and call queue_outreach_email again."},
            indent=2,
        )

    record = {
        "to": to_email,
        "subject": subject,
        "body": body,
        "persona": persona,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }

    if _SETTINGS.dry_run:
        # Save a reviewable draft; nothing leaves the building.
        fname = _OUTBOX / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}_{to_email.replace('@', '_at_')}.json"
        fname.write_text(json.dumps(record, indent=2))
        return json.dumps(
            {"status": "drafted",
             "saved_to": str(fname),
             "note": "DRY-RUN: draft saved for human approval. Nothing was sent."},
            indent=2,
        )

    # INTEGRATION: live send path — wire to Gmail MCP, e.g.
    #   mcp__Gmail__create_draft (recommended: create a draft for final review)
    # then optionally promote to send. We intentionally stop at draft creation
    # to keep a human in the loop on anything that reaches a real inbox.
    return json.dumps(
        {"status": "send_requested",
         "to": to_email,
         "note": "Live mode: hand off to Gmail integration (create_draft)."},
        indent=2,
    )


@beta_tool
def propose_meeting(prospect_name: str, prospect_email: str, suggested_times: str) -> str:
    """Propose an intro meeting with a prospect.

    In dry-run this records the proposal for human approval. In live mode it
    hands off to the calendar integration. Always offers the prospect the
    self-serve booking link as a low-friction option.

    Args:
        prospect_name: The prospect's full name.
        prospect_email: The prospect's email address.
        suggested_times: Human-readable suggested time windows.
    """
    record = {
        "prospect": prospect_name,
        "email": prospect_email,
        "suggested_times": suggested_times,
        "booking_link": _SETTINGS.calendar_link,
        "proposed_at": datetime.now(timezone.utc).isoformat(),
    }
    if _SETTINGS.dry_run:
        return json.dumps(
            {"status": "proposed (dry-run)", **record,
             "note": "Share the booking link in the email; no calendar hold created."},
            indent=2,
        )
    # INTEGRATION: wire to Google Calendar MCP, e.g.
    #   mcp__Google_Calendar__suggest_time then mcp__Google_Calendar__create_event
    return json.dumps({"status": "calendar handoff requested", **record}, indent=2)


# --------------------------------------------------------------------------- #
# CRM logging
# --------------------------------------------------------------------------- #
@beta_tool
def log_lead(
    company: str,
    contact_name: str,
    contact_email: str,
    tier: str,
    summary: str,
    next_step: str,
) -> str:
    """Log a qualified lead and the decided next step to the CRM.

    Call this once you've researched, scored, and decided on a prospect, so the
    pipeline has a durable record. Optionally also posts a summary to Slack.

    Args:
        company: Company name.
        contact_name: Primary contact's name.
        contact_email: Primary contact's email.
        tier: Fit tier from score_lead (A/B/C/disqualified).
        summary: Two-to-three sentence summary of the opportunity.
        next_step: The concrete next action (e.g. "await reply, follow up in 3d").
    """
    entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "company": company,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "tier": tier,
        "summary": summary,
        "next_step": next_step,
    }
    with _CRM.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")

    # INTEGRATION: optionally also push to Slack / Notion, e.g.
    #   mcp__Slack__slack_send_message(channel=_SETTINGS.slack_channel, ...)
    #   mcp__Notion__notion-create-pages(...)
    slack_note = (
        f"would post to Slack channel {_SETTINGS.slack_channel}"
        if _SETTINGS.slack_channel else "no Slack channel configured"
    )
    return json.dumps(
        {"status": "logged", "crm_file": str(_CRM), "slack": slack_note},
        indent=2,
    )


# The ordered tool set handed to the agent.
ALL_TOOLS = [
    research_account,
    score_lead,
    queue_outreach_email,
    propose_meeting,
    log_lead,
]
