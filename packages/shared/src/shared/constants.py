# Standard Reach Gate View Thresholds
DEFAULT_REACH_GATES = [
    300,        # Gate 1: Initial virality tripwire (cheap classifier pass)
    3_000,      # Gate 2: Community feed threshold (ensemble model check)
    30_000,     # Gate 3: Viral threshold (mandatory triage sampling)
    300_000,    # Gate 4: Massive reach (mandatory human look if unverified)
    3_000_000,  # Gate 5: Hard bound (cannot reach without human verification)
]

RISK_DIMENSIONS = {
    'civil_unrest': {'name': 'civil_unrest', 'half_life_days': 30, 'proximity_sigma_km': 25},
    'terrorism': {'name': 'terrorism', 'half_life_days': 90, 'proximity_sigma_km': 50},
    'violent_crime': {'name': 'violent_crime', 'half_life_days': 180, 'proximity_sigma_km': 25},
    'espionage': {'name': 'espionage', 'half_life_days': 365, 'proximity_sigma_km': None},
    'health_medical': {'name': 'health_medical', 'half_life_days': 60, 'proximity_sigma_km': None},
    'natural_hazards': {'name': 'natural_hazards', 'half_life_days': 14, 'proximity_sigma_km': 100},
    'legal_detention': {'name': 'legal_detention', 'half_life_days': 365, 'proximity_sigma_km': None},
    'infrastructure': {'name': 'infrastructure', 'half_life_days': 30, 'proximity_sigma_km': 50},
}

ADMIRALTY_RELIABILITY_WEIGHTS = {'A': 1.0, 'B': 0.8, 'C': 0.6, 'D': 0.3, 'E': 0.1, 'F': 0.5}
ADMIRALTY_CREDIBILITY_WEIGHTS = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.3, 5: 0.1, 6: 0.5}

ICD203_TERMS = [
    ('almost no chance', 0.01, 0.05),
    ('very unlikely', 0.05, 0.20),
    ('unlikely', 0.20, 0.45),
    ('roughly even chance', 0.45, 0.55),
    ('likely', 0.55, 0.80),
    ('very likely', 0.80, 0.95),
    ('almost certain', 0.95, 0.99),
]

SCORE_BANDS = [
    ('LOW', 0.0, 1.5, 'Approve — standard protocols'),
    ('GUARDED', 1.5, 2.5, 'Approve — brief traveler on flagged dimensions'),
    ('MODERATE', 2.5, 3.5, 'Approve with enhanced protocols'),
    ('HIGH', 3.5, 4.3, 'Director decision required'),
    ('SEVERE', 4.3, 5.0, 'Recommend against travel'),
]

STATE_DEPT_LEVEL_TO_BASE = {1: 0.5, 2: 1.5, 3: 3.0, 4: 4.5}

MITIGATION_CREDITS = {
    'executive_protection_detail': 0.30,
    'vetted_transport': 0.20,
    'clean_device_protocol': 0.45,
    'vetted_hotel': 0.15,
    'local_counsel': 0.25,
    'executive_protection': 0.30,
    'secure_transport': 0.20,
    'low_profile': 0.10,
}
