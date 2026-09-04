"""Every test module gets its own database. The two APIs create their engines lazily from DATABASE_URL on first use,
so without this the first module to run fixes the engine for the whole session and later modules read each other's
state (INTSUMs dated tomorrow, ledger events from other tests). Autouse, module-scoped, runs before each module's own
fixtures."""
import os
import tempfile

import pytest


@pytest.fixture(scope="module", autouse=True)
def _fresh_database():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp.name}"
    import coptoc.routes as cop
    import sigtoc.api as s2
    for m in (cop, s2):
        m._engine = None
        m._sessions = None
    yield
    for m in (cop, s2):
        m._engine = None
        m._sessions = None
