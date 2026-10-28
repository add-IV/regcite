"""The regulations in the corpus, pinned to consolidated versions.

Pins are the latest consolidated version in force on 2026-10-28. The MDR has a
2026-11-09 version published but not yet applicable, so it is not used.
"""

from __future__ import annotations

from dataclasses import dataclass

RESOLVER_URL = "http://publications.europa.eu/resource/celex"


@dataclass(frozen=True)
class Source:
    doc_id: str
    title: str
    celex: str  # consolidated CELEX, e.g. 02024R1689-20260727

    @property
    def url(self) -> str:
        return f"{RESOLVER_URL}/{self.celex}"

    @property
    def consolidated(self) -> str:
        stamp = self.celex.rsplit("-", 1)[1]
        return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}"


SOURCES = [
    Source(
        "ai_act", "Artificial Intelligence Act (Regulation (EU) 2024/1689)", "02024R1689-20260727"
    ),
    Source("mdr", "Medical Devices Regulation (Regulation (EU) 2017/745)", "02017R0745-20260719"),
    Source(
        "ivdr", "In Vitro Diagnostic Regulation (Regulation (EU) 2017/746)", "02017R0746-20250110"
    ),
    Source(
        "gdpr",
        "General Data Protection Regulation (Regulation (EU) 2016/679)",
        "02016R0679-20160504",
    ),
]
