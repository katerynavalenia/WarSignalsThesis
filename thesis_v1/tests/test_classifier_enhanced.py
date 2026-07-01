"""
Tests for the enhanced source classifier in src/data/gdelt.py
=============================================================

Tests the hybrid classifier (domain + country + TLD) added in Phase 3B
of the enrichment plan. Covers:
  - GKG country code mapping (UP, RS, UK, EI, GM, IS, JA, KS)
  - Priority logic: domain > country > TLD > other
  - YAML boolean bug fix (NO must be quoted)
  - TLD heuristic for common TLDs
  - "other" fallback for unknown sources
  - DataFrame wrapper classify_all_articles_enhanced()
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.data.gdelt import (
    _load_country_groups,
    _tld_group,
    classify_all_articles_enhanced,
    classify_source_enhanced,
)

CONFIG_DIR = Path("config")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def groups():
    """Load source_groups.yaml."""
    with open(CONFIG_DIR / "source_groups.yaml") as f:
        cfg = yaml.safe_load(f)
    return cfg["groups"]


@pytest.fixture
def country_groups():
    """Load country_groups.yaml."""
    return _load_country_groups(CONFIG_DIR / "country_groups.yaml")


# ─────────────────────────────────────────────────────────────────────────────
# _load_country_groups
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadCountryGroups:
    def test_loads_yaml_successfully(self, country_groups):
        assert isinstance(country_groups, dict)
        assert len(country_groups) > 30  # Should have 40+ country codes

    def test_ukraine_mapped(self, country_groups):
        assert country_groups["UA"] == "ukrainian"
        assert country_groups["UP"] == "ukrainian"  # GKG code

    def test_russia_mapped(self, country_groups):
        assert country_groups["RU"] == "russian"
        assert country_groups["RS"] == "russian"  # GKG code

    def test_us_mapped(self, country_groups):
        assert country_groups["US"] == "western"

    def test_uk_mapped(self, country_groups):
        """GKG code for United Kingdom."""
        assert country_groups["UK"] == "western"

    def test_german_aliases(self, country_groups):
        assert country_groups["DE"] == "western"
        assert country_groups["GM"] == "western"  # GKG code for Germany

    def test_irish_aliases(self, country_groups):
        assert country_groups["IE"] == "western"
        assert country_groups["EI"] == "western"  # GKG code for Ireland

    def test_israel_mapped(self, country_groups):
        """GKG uses IS for Israel, not Iceland."""
        assert country_groups["IL"] == "western"
        assert country_groups["IS"] == "western"  # GKG code for Israel

    def test_japan_aliases(self, country_groups):
        assert country_groups["JP"] == "western"
        assert country_groups["JA"] == "western"  # GKG code for Japan

    def test_korea_aliases(self, country_groups):
        assert country_groups["KR"] == "western"
        assert country_groups["KS"] == "western"  # GKG code for South Korea

    def test_yaml_boolean_bug_fixed(self, country_groups):
        """Regression test: 'NO' must not be parsed as boolean False."""
        # If the YAML had unquoted 'NO', it would be parsed as bool False
        # and this key would be missing or wrong type.
        assert "NO" in country_groups
        assert country_groups["NO"] == "western"
        # Verify the value is a string, not a bool
        assert isinstance(country_groups["NO"], str)

    def test_no_bool_values_in_groups(self, country_groups):
        """All values in the dict should be strings, not booleans."""
        for code, group in country_groups.items():
            assert isinstance(code, str)
            assert isinstance(group, str), (
                f"Country {code!r} mapped to non-string {group!r} "
                f"(type {type(group).__name__})"
            )


# ─────────────────────────────────────────────────────────────────────────────
# _tld_group
# ─────────────────────────────────────────────────────────────────────────────

class TestTldGroup:
    @pytest.mark.parametrize("domain,expected", [
        ("kyivpost.com", "other"),  # .com not in TLD map
        ("ukrinform.ua", "ukrainian"),
        ("sputniknews.ru", "russian"),
        ("bbc.co.uk", "western"),
        ("cnn.com", "other"),  # .com
        ("spiegel.de", "western"),
        ("lemonde.fr", "western"),
        ("reuters.com", "other"),
        ("theguardian.com", "other"),
    ])
    def test_tld_mapping(self, domain, expected):
        assert _tld_group(domain) == expected

    def test_empty_domain(self):
        assert _tld_group("") == "other"

    def test_no_tld(self):
        assert _tld_group("localhost") == "other"

    def test_www_prefix_stripped(self):
        # Function should handle domains with www
        result = _tld_group("www.bbc.co.uk")
        assert result == "western"

    def test_case_insensitive(self):
        assert _tld_group("BBC.CO.UK") == "western"
        assert _tld_group("Ukrinform.UA") == "ukrainian"


# ─────────────────────────────────────────────────────────────────────────────
# classify_source_enhanced
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifySourceEnhanced:
    def test_domain_priority_over_country(self, groups, country_groups):
        """Manual domain curation should win over country mapping."""
        # kyivpost.com is in ukrainian group
        # But if countries says "US" (e.g., CDN serves from US),
        # domain should still win
        result, method = classify_source_enhanced(
            "kyivpost.com",
            countries="US",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "ukrainian"
        assert method == "domain"

    def test_country_mapping_gkg_ukraine(self, groups, country_groups):
        """GKG code UP should map to ukrainian."""
        result, method = classify_source_enhanced(
            "some-ukrainian-domain.com",
            countries="UP;RS",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "ukrainian"
        assert method == "country"

    def test_country_mapping_gkg_russia(self, groups, country_groups):
        """GKG code RS should map to russian."""
        result, method = classify_source_enhanced(
            "some-russian-domain.com",
            countries="RS;UP",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "russian"
        assert method == "country"

    def test_country_mapping_western_aggregator(self, groups, country_groups):
        """yahoo.com (no domain match) should be classified by country."""
        result, method = classify_source_enhanced(
            "yahoo.com",
            countries="US;UP",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "western"
        assert method == "country"

    def test_tld_fallback(self, groups, country_groups):
        """TLD heuristic should apply when no domain/country match."""
        # .co.uk domain, no country info
        result, method = classify_source_enhanced(
            "random-uk-site.co.uk",
            countries="",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "western"
        assert method == "tld"

    def test_tld_ukrainian(self, groups, country_groups):
        result, method = classify_source_enhanced(
            "unknown-ua-site.ua",
            countries="",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "ukrainian"
        assert method == "tld"

    def test_tld_russian(self, groups, country_groups):
        result, method = classify_source_enhanced(
            "unknown-ru-site.ru",
            countries="",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "russian"
        assert method == "tld"

    def test_other_fallback(self, groups, country_groups):
        """Unknown domain + unknown country + unknown TLD → other."""
        result, method = classify_source_enhanced(
            "random-name.indiatimes.com",
            countries="IN",  # India = other
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "other"
        assert method in ("country", "fallback")  # IN not in our map → fallback

    def test_www_prefix_handled(self, groups, country_groups):
        """www. prefix should be stripped before lookup."""
        result, method = classify_source_enhanced(
            "www.kyivpost.com",
            countries="",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "ukrainian"
        assert method == "domain"

    def test_empty_domain(self, groups, country_groups):
        """Empty domain should fall through to country or TLD."""
        result, method = classify_source_enhanced(
            "",
            countries="UP",
            groups=groups,
            country_groups=country_groups,
        )
        # Empty domain skips domain lookup, country takes over
        assert result == "ukrainian"
        assert method == "country"

    def test_none_domain(self, groups, country_groups):
        """None domain should not crash."""
        result, method = classify_source_enhanced(
            None,
            countries="UP",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "ukrainian"
        assert method == "country"

    def test_nan_domain(self, groups, country_groups):
        """NaN domain should not crash."""
        import math
        result, method = classify_source_enhanced(
            float("nan"),
            countries="UP",
            groups=groups,
            country_groups=country_groups,
        )
        assert result == "ukrainian"
        assert method == "country"


# ─────────────────────────────────────────────────────────────────────────────
# classify_all_articles_enhanced
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyAllArticlesEnhanced:
    def test_adds_source_group_column(self, groups, country_groups):
        df = pd.DataFrame({
            "domain": ["kyivpost.com", "tass.com", "cnn.com", "unknown.indiatimes.com"],
            "countries": ["UP", "RS;UP", "US;UP", "IN"],
        })
        result = classify_all_articles_enhanced(df)
        assert "source_group" in result.columns
        assert "classification_method" in result.columns
        assert result.loc[0, "source_group"] == "ukrainian"
        assert result.loc[1, "source_group"] == "russian"
        assert result.loc[2, "source_group"] == "western"
        assert result.loc[3, "source_group"] == "other"

    def test_works_without_countries_column(self, groups, country_groups):
        """Should fall back to simple domain classifier if no countries."""
        df = pd.DataFrame({
            "domain": ["kyivpost.com", "tass.com", "unknown.com"],
        })
        result = classify_all_articles_enhanced(df)
        assert "source_group" in result.columns
        assert "classification_method" in result.columns
        # All should be 'domain' method since no countries
        assert all(result["classification_method"] == "domain")
        # kyivpost and tass should be classified, unknown.com should be other
        assert result.loc[0, "source_group"] == "ukrainian"
        assert result.loc[1, "source_group"] == "russian"
        assert result.loc[2, "source_group"] == "other"

    def test_preserves_original_columns(self, groups, country_groups):
        df = pd.DataFrame({
            "domain": ["kyivpost.com"],
            "url": ["https://kyivpost.com/article"],
            "tone_avg": [-5.0],
        })
        result = classify_all_articles_enhanced(df)
        assert "url" in result.columns
        assert "tone_avg" in result.columns
        assert result.loc[0, "url"] == "https://kyivpost.com/article"
        assert result.loc[0, "tone_avg"] == -5.0

    def test_empty_dataframe(self, groups, country_groups):
        df = pd.DataFrame(columns=["domain", "countries"])
        result = classify_all_articles_enhanced(df)
        assert "source_group" in result.columns
        assert len(result) == 0

    def test_handles_large_batch(self, groups, country_groups):
        """Test with 10K rows to verify performance."""
        import random
        random.seed(42)
        domains = ["kyivpost.com", "tass.com", "cnn.com", "unknown.indiatimes.com"]
        countries = ["UP", "RS", "US", "IN"]
        df = pd.DataFrame({
            "domain": [random.choice(domains) for _ in range(10000)],
            "countries": [random.choice(countries) for _ in range(10000)],
        })
        result = classify_all_articles_enhanced(df)
        assert len(result) == 10000
        assert set(result["source_group"].unique()).issubset(
            {"ukrainian", "russian", "western", "other"}
        )
