"""Country names ↔ ISO codes, enough for the feeds we read. Country-scoped reporting (advisories, health notices, news
situations) has no coordinates; it attaches to requirements by country. Unknown names stay as lower-cased names."""
import re
from typing import Optional

NAMES = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada", "MX": "Mexico", "BR": "Brazil", "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",
    "FR": "France", "DE": "Germany", "ES": "Spain", "PT": "Portugal", "IT": "Italy", "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland", "AT": "Austria",
    "IE": "Ireland", "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland", "PL": "Poland", "CZ": "Czechia", "HU": "Hungary", "GR": "Greece", "TR": "Türkiye",
    "UA": "Ukraine", "RU": "Russia", "IL": "Israel", "SA": "Saudi Arabia", "AE": "United Arab Emirates", "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman",
    "IQ": "Iraq", "IR": "Iran", "JO": "Jordan", "LB": "Lebanon", "EG": "Egypt", "MA": "Morocco", "TN": "Tunisia", "DZ": "Algeria", "LY": "Libya", "SD": "Sudan",
    "ET": "Ethiopia", "KE": "Kenya", "UG": "Uganda", "TZ": "Tanzania", "NG": "Nigeria", "GH": "Ghana", "ZA": "South Africa", "CD": "Democratic Republic of the Congo",
    "IN": "India", "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka", "NP": "Nepal", "CN": "China", "HK": "Hong Kong", "TW": "Taiwan", "JP": "Japan", "KR": "South Korea",
    "KP": "North Korea", "SG": "Singapore", "MY": "Malaysia", "ID": "Indonesia", "TH": "Thailand", "VN": "Vietnam", "PH": "Philippines", "AU": "Australia", "NZ": "New Zealand",
    "YE": "Yemen", "SY": "Syria", "AF": "Afghanistan", "MM": "Myanmar", "VE": "Venezuela", "HT": "Haiti", "CU": "Cuba", "DO": "Dominican Republic", "PA": "Panama", "CR": "Costa Rica",
}
ALIASES = {"usa": "US", "u.s.": "US", "united states of america": "US", "uk": "GB", "u.k.": "GB", "britain": "GB", "great britain": "GB", "england": "GB", "scotland": "GB",
           "turkey": "TR", "korea, republic of": "KR", "republic of korea": "KR", "korea": "KR", "russian federation": "RU", "iran, islamic republic of": "IR",
           "czech republic": "CZ", "drc": "CD", "congo, democratic republic of the": "CD", "the democratic republic of the congo": "CD", "hong kong sar": "HK",
           "viet nam": "VN", "uae": "AE", "ksa": "SA", "holland": "NL", "burma": "MM", "taiwan, province of china": "TW", "the netherlands": "NL", "the philippines": "PH"}
_BY_NAME = {v.lower(): k for k, v in NAMES.items()}


def to_iso(name: Optional[str]) -> Optional[str]:
    """'Saudi Arabia' → 'SA'; 'SA' → 'SA'; unknown → the lower-cased name (still matchable with itself)."""
    if not name: return None
    s = name.strip()
    if len(s) == 2 and s.upper() in NAMES: return s.upper()
    key = s.lower().rstrip(".")
    return _BY_NAME.get(key) or ALIASES.get(key) or (key if key else None)


def country_from_place(text: Optional[str]) -> Optional[str]:
    """'Lisbon, Portugal' → 'PT'; 'Riyadh, Saudi Arabia' → 'SA'; 'London Office' → None (the wall knows the site's country)."""
    if not text: return None
    parts = [p.strip() for p in re.split(r"[,–-]", text) if p.strip()]
    for cand in reversed(parts):
        iso = to_iso(cand)
        if iso and iso in NAMES: return iso
    return None


def name_of(iso: Optional[str]) -> str:
    return NAMES.get(iso or "", iso or "")
