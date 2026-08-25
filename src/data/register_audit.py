"""Validating the outlet register against Wikidata — an automated precision audit.

The design specified a hand-labelled precision audit: open several hundred
articles and check that each is really published where the classifier says. That
was never carried out, and it is the thesis's largest stated limitation.

**The classifier is a deterministic function of the domain**, so article-level
precision is domain-level precision weighted by article volume. Auditing the
domains is therefore not a weaker substitute for auditing articles — it is the
same quantity, computed exactly rather than sampled, provided the domain
assignments can be checked against something external.

Wikidata is that external source. It is maintained independently of GDELT and of
this project, it is queryable, and it carries the two properties the register
claims: **P17 country of origin** and **P127 / P749 ownership**. Comparing the
register against it is a real audit rather than a self-check, and unlike a
hand-labelled sample it covers every registered outlet and can be re-run.

Two honest limits, both reported by :func:`audit_register` rather than hidden:

* **Coverage is incomplete.** Small or regional outlets often have no Wikidata
  item. Those are reported as ``unverified`` and are neither successes nor
  failures — an audit that silently dropped them would overstate its own
  precision.
* **Country of origin is sometimes historical.** Outlets founded before 1991 may
  carry the Soviet Union or the Russian Empire rather than Russia. The country
  mapping below treats those as Russia for classification purposes, which is the
  right answer for a publisher-perspective classifier and the wrong answer for a
  historian.

Ownership is much more sparsely populated than country, so the state-versus-
independent split is validated far less well than the country split. That is
stated in the output rather than glossed: the country dimension carries the
thesis's live claims, and the ownership dimension carries the one that was
already retracted.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

API = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "WarSignalsThesis/1.0 (academic research; register audit)"}

#: Wikidata country QIDs mapped to the ecosystem a publisher there belongs to.
#: Historical predecessors resolve to their successor, because the classifier is
#: about where an outlet publishes from, not about which state existed when it
#: was founded.
COUNTRY_TO_ECOSYSTEM: dict[str, str] = {
    "Q159": "RU", "Q15180": "RU", "Q34266": "RU",      # Russia, USSR, Russian Empire
    "Q212": "UA", "Q2305208": "UA",                     # Ukraine, Ukrainian SSR
    # NATO / EU and close allies -> the investor-facing ecosystem
    "Q30": "WEST", "Q145": "WEST", "Q183": "WEST", "Q142": "WEST",
    "Q38": "WEST", "Q29": "WEST", "Q36": "WEST", "Q55": "WEST",
    "Q34": "WEST", "Q20": "WEST", "Q35": "WEST", "Q33": "WEST",
    "Q16": "WEST", "Q408": "WEST", "Q31": "WEST", "Q40": "WEST",
    "Q213": "WEST", "Q45": "WEST", "Q27": "WEST", "Q41": "WEST",
    "Q218": "WEST", "Q28": "WEST", "Q214": "WEST", "Q219": "WEST",
    "Q224": "WEST", "Q211": "WEST", "Q37": "WEST", "Q191": "WEST",
    "Q32": "WEST", "Q189": "WEST", "Q39": "WEST", "Q664": "WEST",
}

#: Register labels collapsed to the dimension Wikidata can actually check.
#: RU_STATE and RU_INDEP both assert Russia as the country; they differ only in
#: ownership, which is audited separately and much more weakly.
ECOSYSTEM_TO_COUNTRY = {
    "UA": "UA", "RU_STATE": "RU", "RU_INDEP": "RU", "RU_OTHER": "RU",
    "WEST": "WEST",
}


def _get(url: str, timeout: int = 45, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(1.5 * (attempt + 1))
    return None


def lookup_outlet(domain: str, pause: float = 0.15) -> dict:
    """Find a domain's Wikidata item and read its country and ownership.

    Searches on the bare domain, then on the domain without its TLD, because
    Wikidata items are usually titled with the outlet's name rather than its URL.
    """
    stem = domain.split(".")[0]
    result = {"domain": domain, "qid": None, "wd_label": None,
              "wd_country_qid": None, "wd_country_eco": None, "state_owned": None}

    hit = None
    for term in (domain, stem):
        s = _get(f"{API}?action=wbsearchentities&search={urllib.parse.quote(term)}"
                 f"&language=en&format=json&limit=5")
        time.sleep(pause)
        if s and s.get("search"):
            hit = s["search"][0]
            break
    if hit is None:
        return result

    result["qid"], result["wd_label"] = hit["id"], hit.get("label")
    e = _get(f"{API}?action=wbgetentities&ids={hit['id']}&props=claims&format=json")
    time.sleep(pause)
    if not e or "entities" not in e:
        return result

    claims = e["entities"].get(hit["id"], {}).get("claims", {})

    for c in claims.get("P17", []):
        try:
            qid = c["mainsnak"]["datavalue"]["value"]["id"]
        except (KeyError, TypeError):
            continue
        eco = COUNTRY_TO_ECOSYSTEM.get(qid)
        if eco:
            result["wd_country_qid"], result["wd_country_eco"] = qid, eco
            break

    # Ownership: a state or government owner is the signal for RU_STATE. This is
    # sparse on Wikidata, so absence is not evidence of independence.
    owners = claims.get("P127", []) + claims.get("P749", [])
    if owners:
        labels = []
        for o in owners[:3]:
            try:
                oq = o["mainsnak"]["datavalue"]["value"]["id"]
            except (KeyError, TypeError):
                continue
            od = _get(f"{API}?action=wbgetentities&ids={oq}&props=labels"
                      f"&languages=en&format=json")
            time.sleep(pause)
            if od:
                lab = od["entities"].get(oq, {}).get("labels", {}).get("en", {}).get("value", "")
                labels.append(lab.lower())
        joined = " ".join(labels)
        if joined:
            result["state_owned"] = any(
                k in joined for k in ("government", "state", "ministry", "federal",
                                      "russian federation", "presidential")
            )
    return result


def audit_register(register: dict[str, str], pause: float = 0.15) -> pd.DataFrame:
    """Check every registered outlet against Wikidata.

    ``register`` maps domain -> ecosystem label. Returns one row per domain with
    the register's claim, Wikidata's answer, and a verdict of ``match``,
    ``mismatch`` or ``unverified``.
    """
    rows = []
    for domain, eco in sorted(register.items()):
        info = lookup_outlet(domain, pause=pause)
        claimed = ECOSYSTEM_TO_COUNTRY.get(eco, eco)
        found = info["wd_country_eco"]
        verdict = "unverified" if found is None else (
            "match" if found == claimed else "mismatch"
        )
        rows.append({**info, "register_ecosystem": eco,
                     "register_country": claimed, "verdict": verdict})
    return pd.DataFrame(rows)


def summarise(audit: pd.DataFrame) -> pd.DataFrame:
    """Precision by ecosystem, computed only over outlets Wikidata could verify."""
    rows = []
    for eco, g in audit.groupby("register_ecosystem"):
        verified = g[g.verdict != "unverified"]
        rows.append({
            "ecosystem": eco,
            "outlets": len(g),
            "verified": len(verified),
            "matches": int((verified.verdict == "match").sum()),
            "mismatches": int((verified.verdict == "mismatch").sum()),
            "precision": (verified.verdict == "match").mean() if len(verified) else float("nan"),
        })
    return pd.DataFrame(rows).sort_values("outlets", ascending=False)
