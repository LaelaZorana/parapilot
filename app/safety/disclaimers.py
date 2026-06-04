"""Standing disclaimers and the legal-information framing.

Modeled on the FTC v. DoNotPay guardrails (SPEC §0): everything is legal
INFORMATION, never legal advice, and we never claim to be or replace a lawyer.
"""
from __future__ import annotations

# Short disclaimer attached to every answer envelope.
DISCLAIMER = (
    "ParaPilot provides legal information, not legal advice. It is not a lawyer "
    "and cannot tell you what to do in your specific case. Procedures vary by "
    "county and change over time, always confirm with the cited source or a "
    "licensed Illinois attorney or legal aid."
)

# Longer copy for the first-run modal and the About panel.
DISCLAIMER_LONG = (
    "ParaPilot is an educational tool that explains the Illinois divorce "
    "(dissolution of marriage) process and points you to authoritative sources. "
    "It provides legal information, not legal advice, and using it does not create "
    "an attorney-client relationship. ParaPilot cannot tell you which choice is "
    "right for your situation. Court rules, forms, fees, and deadlines differ by "
    "county and change over time. Before you rely on anything here, verify it "
    "against the cited official source, and for advice about your own case, talk "
    "to a licensed Illinois attorney or legal aid."
)

# One-click "find legal help" link used in the footer + modal.
FIND_HELP_NAME = "Illinois Legal Aid Online: Find Legal Help"
FIND_HELP_URL = "https://www.illinoislegalaid.org/get-legal-help"
