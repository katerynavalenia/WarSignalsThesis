"""Audit the outlet register against Wikidata — the precision check, automated.

Replaces the hand-labelled audit the design specified and the project never
carried out. Because the classifier is a deterministic function of the domain,
checking every registered domain against an independent source is the same
quantity a sampled hand audit estimates, computed exactly instead.

    python scripts/run_register_audit.py
    python scripts/run_register_audit.py --pause 0.3   # gentler on the API

Takes a few minutes: Wikidata is queried two or three times per outlet and the
requests are deliberately paced.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.ecosystems import (  # noqa: E402
    RU_INDEPENDENT,
    RU_STATE,
    UA_REGISTER,
    WEST_REGISTER,
)
from src.data.register_audit import audit_register, summarise  # noqa: E402

OUT_DIR = Path("outputs/tables")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    register: dict[str, str] = {}
    for group, label in ((UA_REGISTER, "UA"), (RU_STATE, "RU_STATE"),
                         (RU_INDEPENDENT, "RU_INDEP"), (WEST_REGISTER, "WEST")):
        for d in group:
            register[d] = label

    print(f"auditing {len(register)} registered outlets against Wikidata ...\n")
    audit = audit_register(register, pause=args.pause)

    print("=== precision by ecosystem (verified outlets only) ===")
    summary = summarise(audit)
    print(summary.round(3).to_string(index=False))

    verified = audit[audit.verdict != "unverified"]
    if len(verified):
        overall = (verified.verdict == "match").mean()
        print(f"\n  overall precision on verifiable outlets: {overall:.3f} "
              f"({len(verified)} of {len(audit)} verifiable)")

    mism = audit[audit.verdict == "mismatch"]
    print(f"\n=== mismatches ({len(mism)}) — each needs a human decision ===")
    if len(mism):
        print(mism[["domain", "register_ecosystem", "wd_label",
                    "wd_country_eco"]].to_string(index=False))
    else:
        print("  none")

    unv = audit[audit.verdict == "unverified"]
    print(f"\n=== unverified ({len(unv)}) — no usable Wikidata country ===")
    print("  " + ", ".join(sorted(unv.domain)[:25]))
    print("  These are neither successes nor failures. Counting them as either")
    print("  would misstate the audit.")

    print("\n=== ownership check (state vs independent) ===")
    ru = audit[audit.register_ecosystem.isin(["RU_STATE", "RU_INDEP"])]
    known = ru[ru.state_owned.notna()]
    if len(known):
        agree = ((known.register_ecosystem == "RU_STATE") == known.state_owned).mean()
        print(f"  ownership resolvable for {len(known)} of {len(ru)} Russian outlets; "
              f"agreement {agree:.3f}")
    print("  Wikidata records ownership far more sparsely than country, so this")
    print("  dimension is validated weakly. It carries the state-versus-independent")
    print("  contrast, which is already reported as underpowered and retracted.")

    audit.to_csv(args.out_dir / "register_audit.csv", index=False)
    summary.to_csv(args.out_dir / "register_audit_summary.csv", index=False)
    print(f"\nwrote {args.out_dir/'register_audit.csv'}")


if __name__ == "__main__":
    main()
