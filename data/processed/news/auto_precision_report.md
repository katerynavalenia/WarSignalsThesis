# Phase 3 — Automated Precision Report

**Generated:** 2026-06-30 17:20:14

## Method

This report replaces the manual 400-article labelling audit.
We treat the **high-confidence** domain→country mapping as a
quasi-ground-truth label.  A domain qualifies when:

- it has at least **100** articles contributing country codes, AND
- the top country accounts for at least **70%** of those votes (`primary_pct`).

For every article in those domains, the expected `source_group` is
derived from the dominant country.  We then check whether the
hybrid classifier's `source_group` matches.

**Domains kept:** 6,480  
**Articles kept:** 11,072,349

## Precision per classification method

| Method | Precision | n_correct / n |
|---|---|---|
| country | 0.858 | 8,432,560 / 9,825,064 |
| domain | 0.960 | 451,647 / 470,304 |
| tld | 0.975 | 29,493 / 30,256 |
| fallback | 0.730 | 545,139 / 746,725 |

## Precision per source group (expected = data-driven)

| Group | Precision | n_correct / n |
|---|---|---|
| ukrainian | 0.365 | 33,227 / 90,993 |
| russian | 0.318 | 34,280 / 107,634 |
| western | 0.903 | 8,846,193 / 9,800,062 |
| other | 0.508 | 545,139 / 1,073,660 |

## Overall

- **Precision:** 0.854
- **n_correct / n:** 9,458,839 / 11,072,349

## Caveats

- This is **agreement** with a data-driven proxy, not a true
  hand-labelled precision.  Domains in the high-confidence set
  are mostly large international outlets whose country of
  publication is unambiguous.
- The `primary_country` field is the **most-mentioned country
  in editorial coverage**, not the country of publication.  A
  Ukrainian outlet covering the Russia–Ukraine war will have
  `primary_country = RS` (Russia) because Russia is mentioned
  in most of its articles.  This systematically deflates the
  per-group precision for the `ukrainian` and `russian` groups
  even when the hybrid classifier is correct.
- The `fallback` row is expected to show high `other` agreement
  — by construction those articles have no country signal and
  the classifier assigns them to `other`.
- For a true precision estimate, label ~50 articles per group
  in `data/processed/news/manual_precision_audit_enriched.csv`
  (deferred; not blocking the thesis).
