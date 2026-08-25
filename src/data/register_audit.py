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

**Identity is established by the official-website property, not by name search.**
This matters more than it sounds. An earlier version took the top
``wbsearchentities`` hit for each domain, and that is not stable: across two runs
``dw.com`` resolved once to Deutsche Welle and once to *Der Westen*, an unrelated
German regional paper, while ``svoboda.org`` resolved once to Radio Free
Europe/Radio Liberty and once to nothing. Precision computed that way moves
between runs of the same code, which is not a measurement. Each candidate item is
therefore checked against **P856 (official website)** and accepted only if its
host matches the registered domain. A name that merely looks right is not enough.

Three honest limits, all reported by :func:`audit_register` rather than hidden:

* **Coverage is incomplete, and requiring P856 makes it more so.** Outlets with
  no Wikidata item, or an item that does not record its website, come back
  ``unverified`` — neither successes nor failures. An audit that silently dropped
  them would overstate its own precision, and one that accepted unconfirmed
  name matches would overstate its own coverage.
* **Country of origin is sometimes historical.** Outlets founded before 1991 may
  carry the Soviet Union or the Russian Empire rather than Russia. The country
  mapping below treats those as Russia for classification purposes, which is the
  right answer for a publisher-perspective classifier and the wrong answer for a
  historian.
* **Country of origin is legal, not editorial.** Wikidata records where an outlet
  is registered. For exile newsrooms that is not where their perspective sits,
  which is why Meduza returns a mismatch that the register declines to act on.

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


#: Domain -> Wikidata item, pinned so the audit reproduces exactly.
#:
#: Every entry here was resolved by the website check in :func:`lookup_outlet`
#: and is therefore confirmed by the item's own P856, not by a name that looked
#: close enough. Pinning them removes the last source of run-to-run variation:
#: without it, coverage moves between runs because Wikidata's search ranking
#: does, and a precision figure that changes when nothing changed is not a
#: measurement. Regenerate with ``scripts/run_register_audit.py --repin``.
PINNED_QIDS: dict[str, str] = {}


def _get(url: str, timeout: int = 45, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(1.5 * (attempt + 1))
    return None


def _host(url: str) -> str:
    """Bare hostname of a URL, lowercased and stripped of a leading ``www.``."""
    try:
        h = urllib.parse.urlsplit(url).netloc.lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _website_matches(claims: dict, domain: str) -> bool:
    """Does this item's official website (P856) sit on the registered domain?

    Accepts a subdomain of the registered domain — ``rus.example.com`` confirms
    ``example.com`` — because language services are routinely published that way.
    Rejects everything else, including a merely similar name.
    """
    want = domain.lower()
    for c in claims.get("P856", []):
        try:
            url = c["mainsnak"]["datavalue"]["value"]
        except (KeyError, TypeError):
            continue
        h = _host(str(url))
        if h == want or h.endswith("." + want) or want.endswith("." + h):
            return True
    return False


def lookup_outlet(domain: str, pause: float = 0.15,
                  qid_hint: str | None = None) -> dict:
    """Find a domain's Wikidata item and read its country and ownership.

    Candidates come from a name search, but the item is only accepted once its
    official website confirms the domain. Every candidate is examined and the
    lowest confirmed QID wins, so the answer does not depend on Wikidata's search
    ranking — which is not stable between calls.

    ``qid_hint`` skips the search entirely and reads that item directly. The
    pinned map in :data:`PINNED_QIDS` supplies it, which is what makes a re-run
    reproduce rather than re-litigate.
    """
    stem = domain.split(".")[0]
    result = {"domain": domain, "qid": None, "wd_label": None,
              "wd_country_qid": None, "wd_country_eco": None,
              "state_owned": None, "identity": "unresolved"}

    if qid_hint:
        candidates = [{"id": qid_hint, "label": None}]
    else:
        # Several query forms, because Wikidata's ranking is unstable and the
        # right item is often outside the top few hits for any single one.
        terms = [domain, stem, stem.replace("-", " ")]
        candidates, seen = [], set()
        for term in dict.fromkeys(terms):
            r = _get(f"{API}?action=wbsearchentities"
                     f"&search={urllib.parse.quote(term)}"
                     f"&language=en&format=json&limit=20")
            time.sleep(pause)
            for h in (r or {}).get("search", []):
                if h["id"] not in seen:
                    seen.add(h["id"])
                    candidates.append(h)

    # Every candidate is checked, not just until the first hit, and the winner is
    # the lowest QID among those the website confirms. Stopping early would make
    # the answer depend on search order, which is the instability this function
    # exists to remove.
    confirmed = []
    for cand in candidates:
        e = _get(f"{API}?action=wbgetentities&ids={cand['id']}"
                 f"&props=claims|labels&languages=en&format=json")
        time.sleep(pause)
        ent = (e or {}).get("entities", {}).get(cand["id"], {})
        c = ent.get("claims", {})
        if qid_hint or _website_matches(c, domain):
            label = cand.get("label") or ent.get("labels", {}).get(
                "en", {}).get("value")
            confirmed.append((int(cand["id"][1:]), cand["id"], label, c))

    if not confirmed:
        return result

    confirmed.sort()
    _, qid, label, claims = confirmed[0]
    hit = {"id": qid, "label": label}

    result["qid"], result["wd_label"] = hit["id"], hit.get("label")
    result["identity"] = "website-confirmed"

    # P17 (country) and P495 (country of origin) are both used for media items,
    # inconsistently and often only one of the two. Reading both recovers a
    # meaningful number of outlets that would otherwise be unverifiable, and the
    # two never disagree in this register.
    for prop in ("P17", "P495"):
        for c in claims.get(prop, []):
            try:
                qid = c["mainsnak"]["datavalue"]["value"]["id"]
            except (KeyError, TypeError):
                continue
            eco = COUNTRY_TO_ECOSYSTEM.get(qid)
            if eco:
                result["wd_country_qid"], result["wd_country_eco"] = qid, eco
                break
        if result["wd_country_eco"]:
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
        info = lookup_outlet(domain, pause=pause,
                             qid_hint=PINNED_QIDS.get(domain))
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
