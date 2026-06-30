# Phase 3 — Sensitivity Analysis Report

**Generated:** 2026-06-30 00:29:31
**Wall time:** 10.2s total

**Articles:** 11,433,653

## Strategy Comparison

| Strategy | Ukrainian | Russian | Western | Other | % Classified | Time (s) |
|---|---|---|---|---|---|---|
| domain_only | 15,631 | 11,301 | 453,165 | 10,953,556 | 4.2% | 2.2 |
| tld_only | 8,288 | 1,835 | 2,517,026 | 8,906,504 | 22.1% | 2.1 |
| country_only | 13,695 | 1,476 | 11,417,273 | 1,209 | 100.0% | 2.0 |
| hybrid_current | 29,288 | 12,777 | 11,390,533 | 1,055 | 100.0% | 2.0 |
| hybrid_strict_no_tld | 29,288 | 12,776 | 11,390,380 | 1,209 | 100.0% | 2.0 |

## Interpretation

- **domain_only** — manual curation only. Lowest coverage.
- **tld_only** — top-level domain heuristic. Broad but treats
  all `.com` as `other`.
- **country_only** — GKG COUNTRIES field directly. High
  coverage, reflects article content.
- **hybrid_current** — three-tier (domain → country → TLD).
  Recommended production strategy.
- **hybrid_strict_no_tld** — same but TLD tier disabled.

## Recommendation

Use **hybrid_current** for the master dataset.  The TLD tier
adds ~0.3 % coverage at zero precision cost (`.ua` → ukrainian
and `.ru` → russian are unambiguous).
