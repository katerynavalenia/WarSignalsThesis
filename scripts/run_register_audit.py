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
from src.data.register_audit import (  # noqa: E402
    PINNED,
    audit_register,
    lookup_outlet,
    summarise,
)

OUT_DIR = Path("outputs/tables")


def repin(register: dict[str, str], pause: float,
          only_missing: bool = False) -> None:
    """Resolve every domain from scratch and rewrite the pinned map in place.

    Slow and deliberately so: it examines every search candidate for every
    domain rather than stopping at the first plausible one. It is meant to be run
    when the register changes, not on every audit.

    ``only_missing`` retries just the unpinned domains and keeps the rest. That
    matters because a request that fails during a long run leaves an outlet
    unpinned *permanently* — indistinguishable, in the map, from an outlet
    Wikidata has never heard of. Retrying the gap recovers the transient ones
    without disturbing what already resolved.
    """
    module = Path(__file__).resolve().parents[1] / "src" / "data" / "register_audit.py"

    pins: dict[str, dict[str, str]] = dict(PINNED) if only_missing else {}
    todo = sorted(d for d in register if not (only_missing and d in pins))
    print(f"re-resolving {len(todo)} outlets"
          f"{' (keeping %d already pinned)' % len(pins) if only_missing else ''}"
          " — this takes a while ...")

    for i, domain in enumerate(todo, 1):
        info = lookup_outlet(domain, pause=pause)
        if info["qid"]:
            pins[domain] = {
                "qid": info["qid"],
                "country": info["wd_country_eco"] or "",
                "label": info["wd_label"] or "",
            }
            print(f"  [{i:3d}/{len(todo)}] {domain:24s} -> {info['qid']:12s} "
                  f"{str(info['wd_country_eco'] or '-'):5s} {info['wd_label']}",
                  flush=True)
        else:
            print(f"  [{i:3d}/{len(todo)}] {domain:24s} -> {info['identity']}",
                  flush=True)

    body = "\n".join(
        f'    "{d}": {{"qid": "{v["qid"]}", "country": "{v["country"]}", '
        f'"label": "{v["label"]}"}},'
        for d, v in sorted(pins.items()))
    src = module.read_text()
    start = src.index("PINNED: dict[str, dict[str, str]] = {")
    end = src.index("\n}", start) + 2
    src = (src[:start] + "PINNED: dict[str, dict[str, str]] = {\n" + body
           + "\n}" + src[end:])
    module.write_text(src)
    print(f"\npinned {len(pins)} of {len(register)} outlets into {module}")
    print("re-run without --repin to produce the audit tables.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--repin", action="store_true",
                    help="re-resolve every domain from scratch and rewrite the "
                         "pinned QID map in src/data/register_audit.py")
    ap.add_argument("--only-missing", action="store_true",
                    help="with --repin, retry only the domains that are not yet "
                         "pinned and keep the existing ones")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    register: dict[str, str] = {}
    for group, label in ((UA_REGISTER, "UA"), (RU_STATE, "RU_STATE"),
                         (RU_INDEPENDENT, "RU_INDEP"), (WEST_REGISTER, "WEST")):
        for d in group:
            register[d] = label

    if args.repin:
        repin(register, args.pause, only_missing=args.only_missing)
        return

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

    # Why an outlet is unverified matters, and the three reasons are different
    # claims about the world. Collapsing them would hide the one that is a
    # defect rather than a limit.
    if "identity" in audit.columns:
        print("\n  why, exactly:")
        REASON = {
            "website-confirmed": "item found and confirmed by its own website "
                                 "(no usable country on it)",
            "unresolved": "no candidate item's website matches the domain",
            "lookup-failed": "a request did not come back — NOT evidence of absence",
        }
        for state, n in audit.identity.value_counts().items():
            n_unv = int((unv.identity == state).sum()) if len(unv) else 0
            print(f"    {state:20s} {n:3d} outlets ({n_unv} of them unverified)"
                  f"  — {REASON.get(state, '')}")
        failed = audit[audit.identity == "lookup-failed"]
        if len(failed):
            print(f"\n    {len(failed)} lookup failure(s): "
                  f"{', '.join(sorted(failed.domain))}")
            print("    Re-run to resolve these; they are network failures, not findings.")

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
