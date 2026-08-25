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
PINNED_QIDS: dict[str, str] = {
    "1prime.ru": "Q4376388",
    "1tv.ru": "Q330067",
    "aif.ru": "Q212256",
    "apnews.com": "Q40469",
    "barrons.com": "Q4863797",
    "bbc.co.uk": "Q9531",
    "bloomberg.com": "Q13975",
    "cnbc.com": "Q1023911",
    "currenttime.tv": "Q55663942",
    "dw.com": "Q153770",
    "economist.com": "Q180089",
    "forbes.com": "Q956568",
    "ft.com": "Q2196240",
    "gazeta.ru": "Q595181",
    "hromadske.ua": "Q15280975",
    "iz.ru": "Q753932",
    "kommersant.ru": "Q1780134",
    "kp.ru": "Q849047",
    "kyivindependent.com": "Q111028947",
    "kyivpost.com": "Q1795015",
    "lenta.ru": "Q658909",
    "life.ru": "Q4042868",
    "marketwatch.com": "Q17068426",
    "mediazona.ca": "Q28135463",
    "moscowtimes.ru": "Q1202611",
    "novayagazeta.eu": "Q111654428",
    "novayagazeta.ru": "Q170135",
    "nytimes.com": "Q9684",
    "obozrevatel.com": "Q4329488",
    "politico.eu": "Q991826",
    "pravda.com.ua": "Q904463",
    "regnum.ru": "Q1977770",
    "ren.tv": "Q1479649",
    "reuters.com": "Q130879",
    "rg.ru": "Q1853433",
    "riafan.ru": "Q48940498",
    "rt.com": "Q22868",
    "smotrim.ru": "Q211511",
    "sputniknews.com": "Q212196",
    "strana.news": "Q30889269",
    "tass.ru": "Q223799",
    "theguardian.com": "Q11148",
    "themoscowtimes.com": "Q1202611",
    "tvrain.ru": "Q155172",
    "ukrinform.net": "Q987030",
    "vesti.ru": "Q628101",
    "vz.ru": "Q1970600",
    "wsj.com": "Q164746",
    "zona.media": "Q28135463",
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


def _chunks(seq, n):
    """Successive n-sized slices — the Wikidata API takes 50 ids per request."""
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


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


def _fetch_entities(batch: list[dict], pause: float) -> dict:
    """Claims and labels for a batch of items, falling back to one at a time.

    A batched request that fails returns nothing for *every* item in it, and the
    caller cannot distinguish that from a batch of items with no matching
    website. Rather than let a dropped request look like an answer, whatever the
    batch omits is retried individually and only genuinely missing items stay
    missing.
    """
    ids = "%7C".join(c["id"] for c in batch)
    e = _get(f"{API}?action=wbgetentities&ids={ids}"
             f"&props=claims%7Clabels&languages=en&format=json")
    time.sleep(pause)
    entities = (e or {}).get("entities", {})
    for cand in [c for c in batch if c["id"] not in entities]:
        one = _get(f"{API}?action=wbgetentities&ids={cand['id']}"
                   f"&props=claims%7Clabels&languages=en&format=json")
        time.sleep(pause)
        got = (one or {}).get("entities", {}).get(cand["id"])
        if got is not None:
            entities[cand["id"]] = got
    return entities


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
        # Two different searches, because they fail differently.
        # ``wbsearchentities`` matches labels and aliases only, so it misses an
        # outlet whose Wikidata item is titled unlike its domain. The full-text
        # ``list=search`` indexes statement values, so it finds items *by their
        # website* -- which is precisely the property being checked, and it
        # recovers outlets the label search cannot see. Ranking in both is
        # unstable, which is why every hit is treated as a candidate and none is
        # trusted until the website confirms it.
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

        r = _get(f"{API}?action=query&list=search"
                 f"&srsearch={urllib.parse.quote(domain)}"
                 f"&format=json&srlimit=20")
        time.sleep(pause)
        for h in (r or {}).get("query", {}).get("search", []):
            qid = h.get("title", "")
            if qid.startswith("Q") and qid not in seen:
                seen.add(qid)
                candidates.append({"id": qid, "label": None})

    # Every candidate is checked, not just until the first hit, and the winner is
    # the lowest QID among those the website confirms. Stopping early would make
    # the answer depend on search order, which is the instability this function
    # exists to remove.
    #
    # Checking them one at a time is what makes that unaffordable: a hundred
    # candidates is a hundred round trips. ``wbgetentities`` takes fifty ids per
    # call, so the same exhaustive check costs two.
    confirmed = []
    # Twenty, not the API's documented fifty: a fifty-item request carrying full
    # claims returns megabytes, and the ones that fail fail silently -- _get
    # swallows the error and the outlet is recorded as unknown to Wikidata rather
    # than as a request that did not come back.
    for batch in _chunks(candidates, 20):
        entities = _fetch_entities(batch, pause)
        for cand in batch:
            ent = entities.get(cand["id"])
            if ent is None:
                # The request for this id did not come back. Recording it as
                # "no match" would file a network failure as evidence that
                # Wikidata does not know the outlet -- the silent-failure class
                # this module exists to avoid. Say so instead.
                result["identity"] = "lookup-failed"
                continue
            c = ent.get("claims", {})
            if qid_hint or _website_matches(c, domain):
                label = cand.get("label") or ent.get("labels", {}).get(
                    "en", {}).get("value")
                confirmed.append((int(cand["id"][1:]), cand["id"], label, c))

    if not confirmed:
        return result

    # Deterministic, but not blindly so. Several items can legitimately carry the
    # same website -- an organisation, its website, a former name -- and the
    # lowest QID among them is often the least informative. Prefer a confirmed
    # candidate that actually records a country, then fall back on the lowest id
    # so the choice never depends on search order.
    def _has_country(claims: dict) -> bool:
        for prop in ("P17", "P495"):
            for c in claims.get(prop, []):
                try:
                    if COUNTRY_TO_ECOSYSTEM.get(
                            c["mainsnak"]["datavalue"]["value"]["id"]):
                        return True
                except (KeyError, TypeError):
                    continue
        return False

    confirmed.sort(key=lambda t: (not _has_country(t[3]), t[0]))
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

    When :data:`PINNED_QIDS` is populated it is authoritative: pinned domains are
    read directly and unpinned ones are reported unverifiable without a search.
    That makes the audit deterministic and quick. On an empty map every domain is
    resolved from scratch, which is what ``--repin`` does.
    """
    # Once a pin map exists it is the *whole* record, and unpinned domains are
    # reported unverifiable rather than searched live. Searching them would
    # reintroduce exactly the instability the pin removes: Wikidata's ranking
    # changes between calls, so a domain that resolves today and not tomorrow
    # would move measured coverage without anything having changed. Re-run with
    # ``--repin`` to fold newly resolvable outlets in deliberately.
    pinned_only = bool(PINNED_QIDS)
    rows = []
    for domain, eco in sorted(register.items()):
        qid = PINNED_QIDS.get(domain)
        if pinned_only and qid is None:
            info = {"domain": domain, "qid": None, "wd_label": None,
                    "wd_country_qid": None, "wd_country_eco": None,
                    "state_owned": None, "identity": "unresolved"}
        else:
            info = lookup_outlet(domain, pause=pause, qid_hint=qid)
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
