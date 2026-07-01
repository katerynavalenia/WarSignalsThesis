"""Feature engineering modules for Phase 5."""
from src.features.attack_features import (
    LARGE_ATTACK_QUANTILE,
    SURPRISE_SERIES,
    SURPRISE_WINDOWS,
    add_attack_features,
    compute_attack_surprise_ar1,
)
from src.features.calendar_features import (
    INVASION_DATE,
    VIX_THRESHOLDS,
    add_calendar_features,
)
from src.features.financial_features import add_financial_features
from src.features.merge import (
    build_daily_master,
    load_attack,
    load_financial,
    load_news_enriched,
    load_news_pivot,
    load_paths_config,
)
from src.features.news_features import (
    ROLLING_WINDOWS,
    SOURCE_GROUPS,
    Z_WINDOW,
    add_news_features,
)

__all__ = [
    "INVASION_DATE",
    "LARGE_ATTACK_QUANTILE",
    "PASSTHROUGH_COLS",
    "ROLLING_WINDOWS",
    "SOURCE_GROUPS",
    "SURPRISE_SERIES",
    "SURPRISE_WINDOWS",
    "VIX_THRESHOLDS",
    "Z_WINDOW",
    "add_attack_features",
    "add_calendar_features",
    "add_financial_features",
    "add_news_features",
    "build_daily_master",
    "compute_attack_surprise_ar1",
    "load_attack",
    "load_financial",
    "load_news_enriched",
    "load_news_pivot",
    "load_paths_config",
]
