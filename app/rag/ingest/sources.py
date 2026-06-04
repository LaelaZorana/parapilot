"""Registry of authoritative IL sources to (re)ingest (SPEC §3)."""
from __future__ import annotations

from typing import List, NamedTuple


class Source(NamedTuple):
    source_id: str
    title: str
    url: str
    publisher: str
    jurisdiction: str
    topic: str


# Authoritative sources. These are the live counterparts of the bundled seed
# snapshot in data/corpus/. `make ingest` refreshes from these URLs.
SOURCES: List[Source] = [
    Source(
        "ilao_getting_divorce",
        "Getting a divorce (Illinois Legal Aid Online)",
        "https://www.illinoislegalaid.org/legal-information/getting-divorce",
        "Illinois Legal Aid Online (ILAO)",
        "IL",
        "divorce",
    ),
    Source(
        "illinoiscourts_forms",
        "Approved Statewide Forms: Divorce, Child Support & Maintenance",
        "https://www.illinoiscourts.gov/forms/approved-forms/forms-circuit-court/divorce-child-support-maintenance",
        "Illinois Courts",
        "IL",
        "forms",
    ),
    Source(
        "illinoiscourts_fee_waiver",
        "Fee Waiver for Civil Cases (Illinois Courts)",
        "https://www.illinoiscourts.gov/forms/approved-forms/forms-approved-forms-circuit-court/fee-waiver-civil",
        "Illinois Courts",
        "IL",
        "forms",
    ),
    Source(
        "rule45_remote",
        "Illinois Supreme Court Rule 45: Remote Appearances",
        "https://www.illinoiscourts.gov/rules/supreme-court-rules/article-i-general-rules",
        "Supreme Court of Illinois",
        "IL",
        "remote_appearance",
    ),
    Source(
        "cookcounty_remote",
        "Cook County: Remote Court Proceedings",
        "https://www.cookcountycourtil.gov/about/remote-court-proceedings",
        "Circuit Court of Cook County",
        "IL-Cook",
        "remote_appearance",
    ),
]
