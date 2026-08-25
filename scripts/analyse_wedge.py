"""The censorship wedge on a fixed outlet panel — Chapter 5 §5.3.

Produces the number the thesis actually claims: Russian state media's tone did
not move across the invasion, measured on outlets present on *both* sides of it.

The fixed panel is the whole point. Ecosystem membership changes at exactly the
event being measured — `echo.msk.ru` was liquidated in March 2022 and falls from
13,951 conflict articles to 1,043, while `meduza.io`, `tvrain.ru`, `zona.media`
and `themoscowtimes.com` leave the sample altogether. An ecosystem-level tone
comparison across that boundary is partly measuring a change of composition, so
this restricts to outlets with at least ``--min-articles`` in each period.

It also produces the negative result that retracted the narrower claim: the
state-versus-independent contrast is directional but not significant, because
only six independent outlets survive the panel restriction.

    python scripts/analyse_wedge.py

Requires BigQuery credentials — this queries at outlet level, which the
committed daily aggregates cannot answer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.ecosystems import RU_INDEPENDENT, RU_STATE  # noqa: E402
from src.data.gdelt_bq import CONFLICT, TABLE, client, run_guarded  # noqa: E402

OUT_DIR = Path("outputs/tables")
INVASION = "2022-02-24"
PRE_START, POST_END = "2021-11-01", "2022-06-05"


def outlet_tone_sql(pre_start: str, post_end: str, invasion: str) -> str:
    """Mean conflict tone per outlet, split either side of the invasion."""
    domains = ", ".join(f"'{d}'" for d in sorted(RU_STATE | RU_INDEPENDENT))
    return f"""
    SELECT
      SourceCommonName AS domain,
      IF(_PARTITIONTIME < TIMESTAMP('{invasion}'), 'pre', 'post') AS period,
      COUNT(*) AS n,
      AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS tone
    FROM {TABLE}
    WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{pre_start}') AND TIMESTAMP('{post_end}')
      AND {CONFLICT}
      AND SourceCommonName IN ({domains})
    GROUP BY domain, period
    """


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-articles", type=int, default=200,
                    help="required in EACH period for an outlet to enter the panel")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    bq = client()
    raw = run_guarded(bq, outlet_tone_sql(PRE_START, POST_END, INVASION),
                      max_tb=0.12, label="wedge_outlets")

    raw["eco"] = raw["domain"].apply(
        lambda d: "RU_STATE" if d in RU_STATE else "RU_INDEP"
    )
    wide = raw.pivot_table(index=["eco", "domain"], columns="period",
                           values=["n", "tone"])
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()

    panel = wide.dropna(subset=["tone_pre", "tone_post"])
    panel = panel[(panel.n_pre >= args.min_articles)
                  & (panel.n_post >= args.min_articles)].copy()
    panel["shift"] = panel.tone_post - panel.tone_pre

    dropped = sorted(set(wide.domain) - set(panel.domain))
    print(f"outlets with >= {args.min_articles} conflict articles in BOTH periods: "
          f"{len(panel)}")
    print(f"  RU_STATE {int((panel.eco == 'RU_STATE').sum())}   "
          f"RU_INDEP {int((panel.eco == 'RU_INDEP').sum())}")
    print(f"dropped (absent or thin one side): {len(dropped)}")
    print("  " + ", ".join(dropped))

    summary = panel.groupby("eco").agg(
        n_outlets=("domain", "size"),
        tone_pre=("tone_pre", "mean"),
        tone_post=("tone_post", "mean"),
        shift=("shift", "mean"),
    )
    print("\n=== fixed-panel tone shift ===")
    print(summary.round(3).to_string())

    state = panel.loc[panel.eco == "RU_STATE", "shift"]
    indep = panel.loc[panel.eco == "RU_INDEP", "shift"]
    if len(state) > 1 and len(indep) > 1:
        t = stats.ttest_ind(state, indep, equal_var=False)
        print(f"\nstate {state.mean():+.3f} (n={len(state)}) vs "
              f"independent {indep.mean():+.3f} (n={len(indep)})")
        print(f"Welch test on the difference in shifts: p = {t.pvalue:.4f}")
        print("\nThe thesis claims the state-versus-UKRAINE contrast, not this one:")
        print("six independent outlets is too thin, and the ecosystem is thin")
        print("precisely because of what is being measured.")

    panel.sort_values(["eco", "shift"]).to_csv(
        args.out_dir / "wedge_fixed_panel.csv", index=False)
    summary.to_csv(args.out_dir / "wedge_summary.csv")
    print(f"\nwrote tables to {args.out_dir}")


if __name__ == "__main__":
    main()
