"""Runtime configuration for the Concentric SDR agent.

All secrets come from the environment — nothing is hardcoded. Copy
`.env.example` to `.env` and fill it in, or export the variables directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


# The model is fixed to Anthropic's most capable Opus-tier model. Adaptive
# thinking + high effort gives the agent room to reason about each prospect
# before it drafts anything.
MODEL = "claude-opus-4-8"
EFFORT = "high"  # low | medium | high | max

# Cap the agentic loop so a runaway never silently burns the budget.
MAX_TOOL_ITERATIONS = 25


@dataclass
class Settings:
    """Operator-tunable settings, resolved from the environment."""

    # Identity used in the email signature / sender line.
    rep_name: str = field(default_factory=lambda: os.getenv("SDR_REP_NAME", "Alex Rivera"))
    rep_title: str = field(default_factory=lambda: os.getenv("SDR_REP_TITLE", "Account Executive"))
    rep_email: str = field(default_factory=lambda: os.getenv("SDR_REP_EMAIL", "alex@concentric.com"))
    calendar_link: str = field(
        default_factory=lambda: os.getenv("SDR_CALENDAR_LINK", "https://calendly.com/concentric/intro")
    )

    # Safety: when True (the default), the agent only *drafts* emails and
    # *proposes* meetings — a human approves before anything is sent. Flip to
    # False only when you have explicit authorization to auto-send.
    dry_run: bool = field(default_factory=lambda: os.getenv("SDR_DRY_RUN", "true").lower() != "false")

    # Where to log qualified-lead summaries (Slack channel id, optional).
    slack_channel: str | None = field(default_factory=lambda: os.getenv("SDR_SLACK_CHANNEL") or None)

    def require_api_key(self) -> None:
        """Fail fast with a clear message if the Anthropic key is missing."""
        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            raise RuntimeError(
                "No Anthropic credentials found. Set ANTHROPIC_API_KEY "
                "(or ANTHROPIC_AUTH_TOKEN) in your environment or .env file."
            )
