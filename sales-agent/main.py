#!/usr/bin/env python3
"""CLI entry point for the Concentric SDR agent.

Examples:
    # Work a single prospect end-to-end (research → qualify → draft → log)
    python main.py --domain acme.com --persona CISO

    # Free-form task
    python main.py "Research finserv-co.com and draft outreach to their Head of Data Security"

    # Interactive chat with the agent
    python main.py --interactive
"""

from __future__ import annotations

import argparse
import sys

from concentric_sdr import ConcentricSDR, Settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Concentric AI autonomous SDR agent")
    parser.add_argument("task", nargs="*", help="A free-form task for the agent.")
    parser.add_argument("--domain", help="Target company domain to work a prospect end-to-end.")
    parser.add_argument("--persona", default="CISO", help="Target buyer persona (default: CISO).")
    parser.add_argument("--interactive", action="store_true", help="Start an interactive session.")
    parser.add_argument(
        "--live", action="store_true",
        help="Disable dry-run. ONLY with authorization — drafts may reach real inboxes.",
    )
    args = parser.parse_args()

    settings = Settings()
    if args.live:
        settings.dry_run = False

    try:
        agent = ConcentricSDR(settings)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    mode = "LIVE" if not settings.dry_run else "dry-run (drafts only)"
    print(f"Concentric SDR ready — mode: {mode}\n")

    if args.interactive:
        print("Type a task, or 'quit' to exit.\n")
        while True:
            try:
                task = input("you > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if task.lower() in {"quit", "exit", "q"}:
                break
            if not task:
                continue
            print("\nagent >", agent.run(task), "\n")
        return 0

    if args.domain:
        task = (
            f"Work the prospect at {args.domain} end-to-end for their {args.persona}: "
            f"research the account, score the lead, draft a tailored outreach email, "
            f"propose a meeting, and log the lead with a next step."
        )
    elif args.task:
        task = " ".join(args.task)
    else:
        parser.print_help()
        return 0

    print("agent >", agent.run(task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
