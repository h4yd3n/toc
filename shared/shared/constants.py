# Standard Reach Gate View Thresholds
DEFAULT_REACH_GATES = [
    300,        # Gate 1: Initial virality tripwire (cheap classifier pass)
    3_000,      # Gate 2: Community feed threshold (ensemble model check)
    30_000,     # Gate 3: Viral threshold (mandatory triage sampling)
    300_000,    # Gate 4: Massive reach (mandatory human look if unverified)
    3_000_000,  # Gate 5: Hard bound (cannot reach without human verification)
]
