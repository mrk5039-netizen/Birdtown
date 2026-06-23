"""The Concentric SDR agent: an autonomous sales development rep.

Built on the Anthropic SDK's beta tool runner, which drives the
research → qualify → write → act loop automatically: it calls Claude, executes
any tools Claude requests, feeds the results back, and repeats until Claude has
no more tool calls to make.
"""

from __future__ import annotations

import anthropic

from . import config, product
from .config import Settings
from .tools import ALL_TOOLS, configure


def build_system_prompt(settings: Settings) -> str:
    """Assemble the agent's operating instructions."""
    mode = "DRY-RUN (draft only, human approves)" if settings.dry_run else "LIVE"
    discovery = "\n".join(f"  - {q}" for q in product.DISCOVERY_QUESTIONS)

    return f"""You are an elite, autonomous Sales Development Representative (SDR) \
for {product.COMPANY}. You work pipeline like a top human SDR: thoughtful, \
research-driven, genuinely helpful, never spammy.

You operate as **{settings.rep_name}, {settings.rep_title}** ({settings.rep_email}).
Current mode: {mode}.

{product.product_briefing()}

## How you work a prospect (your standard play)
1. RESEARCH — call `research_account` on the domain. Enrich before you claim
   any specific fact. Never invent firmographics, metrics, or customer names.
2. QUALIFY — call `score_lead` with what you know. If the lead is
   `disqualified`, say so plainly and stop; do not force-fit Concentric.
3. PERSONALIZE — write ONE tailored cold email for the right persona. Lead with
   THEIR problem (use the persona pain points above), connect it to a specific
   Concentric capability, keep it under ~120 words, one clear ask. No jargon
   dumps, no fake urgency, no "Re:" tricks. Sign as {settings.rep_name}.
4. ACT — call `queue_outreach_email`. If it's rejected for compliance, fix the
   issue and resubmit. Offer a meeting via `propose_meeting` and include the
   booking link {settings.calendar_link} as the low-friction option.
5. RECORD — call `log_lead` with the tier, a crisp summary, and the next step.

## Good discovery questions to weave in (don't ask all at once)
{discovery}

## Hard rules
  - Personalize every message to one prospect. Never bulk-blast.
  - Ground every claim in the product briefing or enriched research. If you
    don't know, say you'll confirm — don't guess.
  - Honor the outreach rules above (opt-out, honest subject, B2B context).
  - In DRY-RUN nothing is sent; you are producing drafts for human approval.
  - If a request would be inappropriate outreach, or you lack the data to do it
    responsibly, stop and explain what you need from the operator.

Be concise in your own narration. Do the work with tools; explain only what the
operator needs to decide or approve."""


class ConcentricSDR:
    """A thin wrapper around the Anthropic tool runner for a sales workflow."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.require_api_key()
        configure(self.settings)
        self.client = anthropic.Anthropic()
        self.system = build_system_prompt(self.settings)
        # Stateless API → we keep the running transcript ourselves.
        self.messages: list[dict] = []

    def run(self, instruction: str) -> str:
        """Give the agent a task (e.g. 'Work the prospect at acme.com for their CISO').

        Returns the agent's final text response. Side effects (drafts, CRM
        entries) are written by the tools as it goes.
        """
        self.messages.append({"role": "user", "content": instruction})

        runner = self.client.beta.messages.tool_runner(
            model=config.MODEL,
            max_tokens=16000,
            system=self.system,
            tools=ALL_TOOLS,
            messages=self.messages,
            thinking={"type": "adaptive"},
            output_config={"effort": config.EFFORT},
            max_iterations=config.MAX_TOOL_ITERATIONS,
        )

        final = None
        for message in runner:
            final = message  # the loop yields each turn; last one is the answer

        # Persist the full assistant turn so multi-task sessions retain context.
        if final is not None:
            self.messages.append({"role": "assistant", "content": final.content})
            return "".join(b.text for b in final.content if b.type == "text").strip()
        return ""
