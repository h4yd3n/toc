"""§4 names and ranks (2026-09-05). A person carries last name, first name, middle initial, a rank abbreviation, and a pay grade.
The grade is the cross-service constant — E1–E9, W1–W5, O1–O10, plus CIV and CTR for civilians and contractors — because
services spell the same grade differently. The rank is what people say ("SSG"). Display follows the profile (the author's call):
military reads LAST, First M. · SSG — last name first so a list sorts the way a roster does, the rank after the name;
corporate reads First Last. Sorting is by last name in both."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Army rank abbreviations by grade (what the seed and the display use); other services' spellings parse to the same grade.
GRADE_RANK = {
    "E1": "PVT", "E2": "PV2", "E3": "PFC", "E4": "SPC", "E5": "SGT", "E6": "SSG", "E7": "SFC", "E8": "MSG", "E9": "SGM",
    "W1": "WO1", "W2": "CW2", "W3": "CW3", "W4": "CW4", "W5": "CW5",
    "O1": "2LT", "O2": "1LT", "O3": "CPT", "O4": "MAJ", "O5": "LTC", "O6": "COL", "O7": "BG", "O8": "MG", "O9": "LTG", "O10": "GEN",
    "CIV": "CIV", "CTR": "CTR",
}
RANK_GRADE: Dict[str, str] = {r: g for g, r in GRADE_RANK.items()}
RANK_GRADE.update({"CPL": "E4", "1SG": "E8", "CSM": "E9", "SMA": "E9", "PV1": "E1", "PVT2": "E2",
                   # other services, to the same grade
                   "PVT": "E1", "AB": "E1", "SR": "E1", "SA": "E2", "SN": "E3", "A1C": "E3", "SRA": "E4", "PO3": "E4", "PO2": "E5", "PO1": "E6", "TSGT": "E6", "MSGT": "E7", "CPO": "E7",
                   "SMSGT": "E8", "SCPO": "E8", "CMSGT": "E9", "MCPO": "E9", "GYSGT": "E7", "LCPL": "E3", "SSGT": "E6",
                   "ENS": "O1", "LTJG": "O2", "LT": "O3", "LCDR": "O4", "CDR": "O5", "CAPT": "O6", "RDML": "O7", "RADM": "O8", "VADM": "O9", "ADM": "O10",
                   "2NDLT": "O1", "1STLT": "O2", "BGEN": "O7", "MAJGEN": "O8", "LTGEN": "O9",
                   "CIVILIAN": "CIV", "GS": "CIV", "CONTRACTOR": "CTR", "KTR": "CTR"})
GRADE_ORDER = {g: i for i, g in enumerate(list(GRADE_RANK))}


def parse_rank(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """'SSG' → ('SSG', 'E6'); 'E-6' → ('SSG', 'E6'); 'Staff Sergeant' is not parsed (reported unset); 'CW3' → ('CW3', 'W3')."""
    t = (text or "").strip().upper().replace("-", "").replace(" ", "")
    if not t:
        return None, None
    if t in GRADE_RANK:
        return GRADE_RANK[t], t
    if t in RANK_GRADE:
        return (t if t in GRADE_RANK.values() or t in ("CPL", "1SG", "CSM", "SMA") else t), RANK_GRADE[t]
    m = re.fullmatch(r"(E|W|O)(\d{1,2})", t)
    if m and m.group(0) in GRADE_RANK:
        return GRADE_RANK[m.group(0)], m.group(0)
    return t, None  # a rank we do not know: keep the text, no grade


def split_name(full: str) -> Tuple[str, str, Optional[str]]:
    """'Avery B. Okafor' → ('Avery', 'Okafor', 'B'); 'Okafor, Avery B.' → the same; 'Avery Okafor' → no initial."""
    full = (full or "").strip()
    if "," in full:
        last, rest = [x.strip() for x in full.split(",", 1)]
        parts = rest.split()
    else:
        parts = full.split()
        last = parts.pop() if len(parts) > 1 else (parts[0] if parts else "")
    first = parts[0] if parts else ""
    mi = next((p.rstrip(".")[0] for p in parts[1:] if p), None)
    return first, last, mi


def display(profile: str, first: Optional[str], last: Optional[str], mi: Optional[str], rank: Optional[str], fallback: str) -> str:
    if not last:
        return fallback
    if profile == "military":
        core = f"{last.upper()}, {first}" + (f" {mi}." if mi else "")
        return f"{core} · {rank}" if rank else core
    return f"{first} {last}".strip()


def short(profile: str, first: Optional[str], last: Optional[str], rank: Optional[str], fallback: str) -> str:
    """The map label: 'SSG Reyes' on a military desk, 'Jordan' on a corporate one."""
    if not last:
        return fallback.split(" ")[0]
    return (f"{rank} {last}" if rank else last) if profile == "military" else (first or last)


def sort_key(last: Optional[str], first: Optional[str], fallback: str) -> str:
    return (f"{last}, {first}" if last else fallback).lower()
