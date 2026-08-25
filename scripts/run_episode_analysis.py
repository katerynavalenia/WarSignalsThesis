"""Detect anticipation episodes and test threat vs act within each — Chapter 5 §5.4.

Produces the episode table the descriptive chapter reports, and the per-episode
threat-versus-act regressions that establish the effect does not replicate
outside the Russian build-up.

**Episodes are detected from GPR alone.** No asset price enters the search. Had
it, the procedure would find windows where the effect exists by construction and
every later test would be circular — so the detector is deliberately blind to the
outcome, and that is the property worth preserving if this is ever re-run.

    python scripts/run_episode_analysis.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.episodes import (  # noqa: E402
    KNOWN_EVENTS,
    anticipation_score,
    find_episodes,
    label_episodes,
)
from src.models.regime_response import channel_race  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

#: Each target takes its own region's benchmark. Using SP500 for European
#: defence is the error Chapter 8 §8.1 documents.
TARGETS = {
    "us_defence": "spx", "eu_defence": "sxxp", "r_ita": "spx",
    "r_waerlst": "spx", "r_bshieldt": "sxxp",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    score = anticipation_score(spine)
    panel = spine.set_index("date")
    panel["lvix"] = np.log(panel["vix_yf"]).shift(1)

    print("=== threshold sensitivity ===")
    for thr in (0.4, 0.5, 0.6, 0.75):
        eps = find_episodes(score, threshold=thr)
        print(f"  threshold {thr}: {len(eps)} episodes, "
              f"{int(eps.n_days.sum()) if len(eps) else 0} days")

    episodes = label_episodes(find_episodes(score, threshold=args.threshold),
                             KNOWN_EVENTS)
    print(f"\n=== episodes at threshold {args.threshold} ===")
    for _, e in episodes.iterrows():
        print(f"  {e.start.date()} -> {e.end.date()}  n={e.n_days:4d}  "
              f"peak={e.peak:5.2f}  {e.label or '(unlabelled)'}")

    rows = []
    for _, e in episodes.iterrows():
        sub = panel.loc[e.start: e.end]
        for target, bench in TARGETS.items():
            if target not in sub or sub[target].notna().sum() < 40:
                continue
            res = channel_race(sub.rename(columns={bench: "r_mkt"}), target)
            if res:
                rows.append({
                    "episode": f"{e.start.date()}..{e.end.date()}",
                    "label": e.label or "(unlabelled)",
                    "target": target, **res,
                })
    per_episode = pd.DataFrame(rows)

    print("\n=== threat vs act within each episode (returns, HAC(5)) ===")
    for target in TARGETS:
        t = per_episode[per_episode.target == target]
        if len(t):
            print(f"\n--- {target} ---")
            print(t[["episode", "label", "n", "act", "p_act", "threat",
                     "p_threat", "r2"]].round(4).to_string(index=False))

    mask = pd.Series(False, index=panel.index)
    for _, e in episodes.iterrows():
        mask.loc[e.start: e.end] = True

    print("\n=== pooled episode days vs non-episode days ===")
    pooled_rows = []
    for label, sub in (("episode days", panel[mask]),
                       ("non-episode days", panel[~mask])):
        for target, bench in TARGETS.items():
            if target not in sub or sub[target].notna().sum() < 40:
                continue
            res = channel_race(sub.rename(columns={bench: "r_mkt"}), target)
            if res:
                pooled_rows.append({"sample": label, "target": target, **res})
    pooled = pd.DataFrame(pooled_rows)
    print(pooled[["sample", "target", "n", "act", "p_act", "threat",
                  "p_threat"]].round(4).to_string(index=False))

    episodes.to_csv(args.out_dir / "episodes.csv", index=False)
    per_episode.to_csv(args.out_dir / "episode_threat_act.csv", index=False)
    pooled.to_csv(args.out_dir / "episode_pooled.csv", index=False)
    print(f"\nwrote three tables to {args.out_dir}")


if __name__ == "__main__":
    main()
