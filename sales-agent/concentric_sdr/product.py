"""Product knowledge base for Concentric AI.

This is the single source of truth the agent uses to ground every piece of
outreach. Keep it factual and current — the agent will quote from it, so
anything inaccurate here becomes an inaccurate claim in a prospect's inbox.
"""

COMPANY = "Concentric AI"
WEBSITE = "https://concentric.com"

# One-paragraph positioning the agent can lean on for any cold opener.
POSITIONING = (
    "Concentric AI is an agentic Data Security Posture Management (DSPM) "
    "platform. It autonomously discovers, classifies, and protects sensitive "
    "data across cloud, on-prem, email, and SaaS — without rules or regex — "
    "using its Semantic Intelligence models. It finds where sensitive data "
    "lives, who can access it, where it's overexposed or wrongly shared, and "
    "remediates risk automatically."
)

# Concrete capabilities, phrased the way a buyer cares about them.
CAPABILITIES = [
    "Autonomous data discovery and classification across 100+ data stores "
    "(M365, Google Workspace, Box, AWS, Azure, Snowflake, on-prem file shares).",
    "Risk detection for overshared, misclassified, and at-risk data without "
    "writing a single rule or regex.",
    "Identity- and access-aware analysis: who can see what, and whether they "
    "should.",
    "Automated remediation of risky sharing and access at scale.",
    "Compliance support for GDPR, HIPAA, PCI, CCPA, and AI-data governance.",
]

# Pains by persona — used to tailor the angle of an opener.
PAIN_POINTS = {
    "CISO": [
        "no clear inventory of where sensitive/regulated data actually lives",
        "data sprawl across SaaS and cloud with unknown exposure",
        "audit and breach risk from overshared files and stale access",
    ],
    "Head of Data Security": [
        "legacy DLP and regex-based classification with high false-positive rates",
        "manual, never-finished classification projects",
        "no way to prioritize the data risk that actually matters",
    ],
    "Compliance / GRC": [
        "proving data handling for GDPR/HIPAA/PCI audits",
        "tracking regulated data across systems for DSARs",
        "governing data used to train internal AI/LLM systems",
    ],
    "IT / Security Engineering": [
        "remediating risky sharing by hand across thousands of files",
        "stitching together point tools for discovery, classification, and access",
    ],
}

IDEAL_CUSTOMER_PROFILE = {
    "company_size": "500+ employees (strongest fit at 1,000+)",
    "industries": [
        "financial services", "healthcare", "technology/SaaS",
        "manufacturing", "insurance", "pharma",
    ],
    "buyer_titles": [
        "CISO", "VP/Director of Information Security", "Head of Data Security",
        "Data Protection Officer", "VP of Governance Risk & Compliance",
    ],
    "triggers": [
        "recent breach or data-exposure incident",
        "new regulatory/audit pressure (GDPR, HIPAA, PCI, AI governance)",
        "cloud or M365/Google Workspace migration",
        "rolling out internal generative-AI tools (data governance need)",
        "replacing legacy DLP / Microsoft Purview frustration",
    ],
}

DISCOVERY_QUESTIONS = [
    "How do you currently know where your sensitive and regulated data lives?",
    "What are you using today for data classification, and how accurate is it?",
    "How do you find and fix overshared or wrongly-accessed data?",
    "Are you governing the data feeding any internal AI/LLM tools yet?",
    "What's driving data-security priority right now — an audit, an incident, a migration?",
]

# Hard guardrails. The agent must never cross these.
OUTREACH_RULES = [
    "Only contact business prospects for legitimate B2B purposes.",
    "Never fabricate customer names, metrics, case studies, or claims.",
    "Never send mass/bulk identical emails — every message is personalized.",
    "Always include a clear, honest reason for reaching out and an easy opt-out.",
    "Respect GDPR/CAN-SPAM: business context only, no deceptive subject lines.",
    "If unsure whether outreach is appropriate, stop and ask the human operator.",
]


def product_briefing() -> str:
    """Render the product context as a system-prompt section."""
    caps = "\n".join(f"  - {c}" for c in CAPABILITIES)
    pains = "\n".join(
        f"  {persona}:\n" + "\n".join(f"    - {p}" for p in items)
        for persona, items in PAIN_POINTS.items()
    )
    icp = IDEAL_CUSTOMER_PROFILE
    triggers = "\n".join(f"  - {t}" for t in icp["triggers"])
    rules = "\n".join(f"  - {r}" for r in OUTREACH_RULES)
    return f"""# Product: {COMPANY} ({WEBSITE})

{POSITIONING}

## What it does
{caps}

## Buyer pains by persona
{pains}

## Ideal customer profile
  Company size: {icp['company_size']}
  Industries: {", ".join(icp['industries'])}
  Buyer titles: {", ".join(icp['buyer_titles'])}
  Buying triggers:
{triggers}

## Non-negotiable outreach rules
{rules}
"""
