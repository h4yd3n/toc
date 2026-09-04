"""The collectors the refresh runs, keyed by catalog id. `configured` is the truth behind the catalog's LIVE chip."""
import os
from typing import Any, Awaitable, Callable, Dict, List, Sequence, Tuple

from . import acled, clstr, fcdo, nws, state_dept, usgs, who_don
from .gdacs import collect_gdacs

Points = Sequence[Tuple[float, float]]
Countries = Dict[str, Tuple[float, float]]  # ISO → a representative blue-force point there

COLLECTORS: Dict[str, Dict[str, Any]] = {
    "gdacs":      {"scope": "point",   "run": lambda p, c: collect_gdacs(p)},
    "usgs":       {"scope": "point",   "run": lambda p, c: usgs.collect_usgs(p)},
    "nws":        {"scope": "point",   "run": lambda p, c: nws.collect_nws(p)},
    "who_don":    {"scope": "country", "run": lambda p, c: who_don.collect_who(p, c)},
    "state_dept": {"scope": "country", "run": lambda p, c: state_dept.collect_state_dept(p, c)},
    "fcdo":       {"scope": "country", "run": lambda p, c: fcdo.collect_fcdo(p, c)},
    "acled":      {"scope": "point",   "run": lambda p, c: acled.collect_acled(p, c), "configured": acled.configured},
    "clstr":      {"scope": "country", "run": lambda p, c: clstr.collect_clstr(p, c), "configured": clstr.configured},
}


def configured(source_id: str) -> bool:
    """TOC_SOURCES_CONFIGURED pins the answer (comma list) — for tests and for an operator who wants to declare what is live."""
    pinned = os.environ.get("TOC_SOURCES_CONFIGURED")
    if pinned is not None:
        return source_id in {x.strip() for x in pinned.split(",") if x.strip()}
    if source_id == "ops": return True
    if source_id == "wikidata": return os.environ.get("TOC_OFFLINE", "") != "1"  # Nager.Date holidays, fetched on demand for the Area Assessment
    c = COLLECTORS.get(source_id)
    if not c: return False
    if os.environ.get("TOC_OFFLINE", "") == "1": return False
    return c["configured"]() if "configured" in c else True


async def run(source_id: str, points: Points, countries: Countries) -> List[Dict[str, Any]]:
    return await COLLECTORS[source_id]["run"](points, countries)
