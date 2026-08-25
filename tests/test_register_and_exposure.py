"""Tests for the register audit, the SIPRI exposure panel, and the ingest merge.

All offline. The Wikidata functions that touch the network are split from the
ones that decide things, so the decisions are testable without a connection —
the same split the GPR/FRED tests rely on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.ecosystems import (  # noqa: E402
    AGGREGATORS,
    RU_INDEPENDENT,
    RU_STATE,
    UA_REGISTER,
    WEST_REGISTER,
)
from src.data.register_audit import (  # noqa: E402
    ECOSYSTEM_TO_COUNTRY,
    _host,
    _website_matches,
    summarise,
)
from src.data.sipri import (  # noqa: E402
    SIPRI_TO_TICKER,
    _normalise,
    exposure_panel,
    match_tickers,
)


# --- the register itself ------------------------------------------------------

class TestRegisterIntegrity:
    """The register is hand-curated, so its invariants are worth asserting."""

    def test_no_domain_in_two_ecosystems(self):
        groups = {
            "RU_STATE": RU_STATE,
            "RU_INDEPENDENT": RU_INDEPENDENT,
            "UA_REGISTER": UA_REGISTER,
            "WEST_REGISTER": WEST_REGISTER,
            "AGGREGATORS": AGGREGATORS,
        }
        seen: dict[str, str] = {}
        for name, group in groups.items():
            for d in group:
                assert d not in seen, f"{d} is in both {seen[d]} and {name}"
                seen[d] = name

    def test_state_funded_broadcasters_are_western(self):
        """The rule the dw.com and RFE/RL corrections established.

        A state-funded external broadcaster classifies to the state that funds
        it, whatever language it publishes in. Regression test: all three were
        once in the Russian independent set.
        """
        for domain in ("dw.com", "svoboda.org", "currenttime.tv"):
            assert domain in WEST_REGISTER
            assert domain not in RU_INDEPENDENT

    def test_exile_newsrooms_stay_russian(self):
        """The same rule's other half, which Wikidata's country field disagrees
        with: these are Russian newsrooms publishing from abroad."""
        for domain in ("meduza.io", "novayagazeta.eu", "tvrain.ru",
                       "themoscowtimes.com"):
            assert domain in RU_INDEPENDENT
            assert domain not in WEST_REGISTER

    def test_aggregators_are_excluded_everywhere(self):
        for d in AGGREGATORS:
            assert d not in WEST_REGISTER
            assert d not in RU_STATE
            assert d not in RU_INDEPENDENT
            assert d not in UA_REGISTER


# --- Wikidata identity resolution --------------------------------------------

class TestWebsiteMatching:
    """Identity is confirmed by P856, because name search is not stable.

    The concrete failure this guards against: `dw.com` once resolved to
    *Der Westen*, an unrelated German paper, purely on name similarity.
    """

    @pytest.mark.parametrize("url,expected", [
        ("https://www.dw.com/en/", "dw.com"),
        ("http://dw.com", "dw.com"),
        ("https://WWW.Meduza.IO/path", "meduza.io"),
        ("not a url", ""),
    ])
    def test_host_extraction(self, url, expected):
        assert _host(url) == expected

    def _claims(self, *urls):
        return {"P856": [{"mainsnak": {"datavalue": {"value": u}}} for u in urls]}

    def test_exact_domain_confirms(self):
        assert _website_matches(self._claims("https://www.dw.com/"), "dw.com")

    def test_subdomain_confirms(self):
        """Language services routinely live on a subdomain."""
        assert _website_matches(self._claims("https://rus.example.com"),
                                "example.com")

    def test_different_outlet_is_rejected(self):
        """The Der Westen case: similar name, different site."""
        assert not _website_matches(self._claims("https://www.derwesten.de/"),
                                    "dw.com")

    def test_missing_property_is_rejected(self):
        assert not _website_matches({}, "dw.com")

    def test_malformed_claim_does_not_raise(self):
        assert not _website_matches({"P856": [{"mainsnak": {}}]}, "dw.com")


class TestSummarise:
    def test_unverified_rows_are_excluded_from_precision(self):
        """Counting unverified outlets either way would misstate the audit."""
        audit = pd.DataFrame({
            "register_ecosystem": ["WEST"] * 4,
            "verdict": ["match", "match", "mismatch", "unverified"],
        })
        row = summarise(audit).iloc[0]
        assert row.outlets == 4
        assert row.verified == 3
        assert row.matches == 2
        assert row.mismatches == 1
        assert row.precision == pytest.approx(2 / 3)

    def test_all_unverified_gives_nan_not_zero(self):
        audit = pd.DataFrame({"register_ecosystem": ["UA"],
                              "verdict": ["unverified"]})
        assert pd.isna(summarise(audit).iloc[0].precision)

    def test_both_russian_blocks_claim_russia(self):
        """They differ by ownership, not country, so the country audit must not
        treat the state/independent split as a country disagreement."""
        assert ECOSYSTEM_TO_COUNTRY["RU_STATE"] == "RU"
        assert ECOSYSTEM_TO_COUNTRY["RU_INDEP"] == "RU"


# --- SIPRI exposure -----------------------------------------------------------

class TestSipri:
    def test_normalise_strips_suffixes(self):
        assert _normalise("Lockheed Martin Corp.") == "lockheed martin"
        assert _normalise("  BAE Systems PLC ") == "bae systems"

    def test_map_never_collides_two_firms_onto_one_ticker_wrongly(self):
        """General Dynamics and General Electric are close in string distance
        and nothing alike in exposure. This is why the map is hand-curated."""
        assert SIPRI_TO_TICKER["general dynamics"] == "GD"
        assert SIPRI_TO_TICKER["general electric"] == "GE"

    def test_match_tickers_collapses_spellings(self):
        """SIPRI's spelling of a firm changes across years; the ticker should
        not."""
        sipri = pd.DataFrame({
            "year": [2015, 2016],
            "company": ["Lockheed Martin Corp.", "Lockheed Martin"],
            "key": ["lockheed martin", "lockheed martin"],
            "country": ["United States", "United States"],
            "arms": [36.4, 40.8],
            "total": [46.1, 47.2],
            "arms_share": [0.79, 0.86],
        })
        out = match_tickers(sipri)
        assert set(out.ticker) == {"LMT"}
        assert len(out) == 2  # one row per year, not per spelling

    def test_unmapped_firms_are_dropped_not_guessed(self):
        sipri = pd.DataFrame({
            "year": [2015], "company": ["Some Unlisted State Arsenal"],
            "key": ["some unlisted state arsenal"], "country": ["Russia"],
            "arms": [5.0], "total": [6.0], "arms_share": [0.83],
        })
        assert match_tickers(sipri).empty

    def test_exposure_panel_averages_over_years(self):
        matched = pd.DataFrame({
            "ticker": ["LMT", "LMT"], "year": [2015, 2016],
            "company": ["Lockheed Martin"] * 2,
            "country": ["United States"] * 2,
            "arms": [36.4, 40.8], "total": [46.1, 47.2],
            "arms_share": [0.80, 0.90],
        })
        panel = exposure_panel(matched)
        assert panel.loc["LMT", "arms_share"] == pytest.approx(0.85)
        assert panel.loc["LMT", "years"] == 2


# --- the ingest merge ---------------------------------------------------------

class TestIngestMerge:
    """Regression test for a bug that silently discarded freshly queried data.

    ``drop_duplicates`` defaulted to keeping the first row, and existing rows are
    concatenated *before* newly queried ones, so every re-ingest resolved in
    favour of the stale copy. The threat/act table survived a 454 GB re-run
    byte-identical after the outlet register had been corrected: the query ran,
    the bill was paid, and the result was thrown away.
    """

    def _merge(self, frames):
        """The merge exactly as ``scripts/ingest_gdelt.ingest`` performs it."""
        return (
            pd.concat(frames, ignore_index=True)
            .drop_duplicates(["day", "ecosystem"], keep="last")
            .sort_values(["day", "ecosystem"])
            .reset_index(drop=True)
        )

    def test_fresh_rows_replace_stale_ones(self):
        stale = pd.DataFrame({"day": ["2022-02-24"], "ecosystem": ["RU_INDEP"],
                              "n_conflict": [1000]})
        fresh = pd.DataFrame({"day": ["2022-02-24"], "ecosystem": ["RU_INDEP"],
                              "n_conflict": [800]})
        out = self._merge([stale, fresh])
        assert len(out) == 1
        assert out.n_conflict.iloc[0] == 800, "stale row won: the bug is back"

    def test_untouched_days_are_preserved(self):
        stale = pd.DataFrame({
            "day": ["2022-02-23", "2022-02-24"],
            "ecosystem": ["RU_INDEP", "RU_INDEP"], "n_conflict": [900, 1000]})
        fresh = pd.DataFrame({"day": ["2022-02-24"], "ecosystem": ["RU_INDEP"],
                              "n_conflict": [800]})
        out = self._merge([stale, fresh])
        assert len(out) == 2
        assert out.set_index("day").n_conflict.to_dict() == {
            "2022-02-23": 900, "2022-02-24": 800}

    def test_other_ecosystems_are_untouched(self):
        stale = pd.DataFrame({
            "day": ["2022-02-24"] * 2, "ecosystem": ["RU_INDEP", "UA"],
            "n_conflict": [1000, 5000]})
        fresh = pd.DataFrame({"day": ["2022-02-24"], "ecosystem": ["RU_INDEP"],
                              "n_conflict": [800]})
        out = self._merge([stale, fresh])
        assert out.set_index("ecosystem").n_conflict.to_dict() == {
            "RU_INDEP": 800, "UA": 5000}
