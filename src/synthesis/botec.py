# Benchmarks are indicative ranges for comparison only; no cross-metric conversion.

BENCHMARKS = {
    "DALY": {
        "name": "GiveWell top charities",
        "usd_per_daly": [100, 500],
    },
    "log_income": {
        "name": "GiveDirectly",
        "relative_effect": 1.0,
    },
    "WELBY": {
        "name": "StrongMinds-like",
        "usd_per_welby": [50, 1000],
    },
    "WALY": {
        "name": "Humane League / ACE",
        "usd_per_animal_year": [0.01, 1.0],
    },
    "CO2": {
        "name": "Frontier climate",
        "usd_per_tco2e": [5, 100],
    },
}

DISCOUNT_SCHEDULE = {
    "up_to_50y": 0.0,
    "beyond_50y": 0.02,
}


