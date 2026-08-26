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

#: Countries that no longer exist. An outlet founded before 1991 often records
#: several states in sequence, and reading the first one is how ``iz.ru``
#: (Izvestia — a Russian newspaper) came back classified as Ukrainian: its item
#: lists the Ukrainian SSR, then the Soviet Union, then Russia, in that order.
#: A present-day state always wins over a predecessor, and only when no
#: present-day state is recorded does a predecessor decide.
HISTORICAL_COUNTRIES = frozenset({"Q15180", "Q34266", "Q2305208"})

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


#: Domain -> the Wikidata item confirmed for it, and what that item says.
#:
#: Every entry was resolved by the website check in :func:`lookup_outlet` and is
#: therefore confirmed by the item's own P856, not by a name that looked close
#: enough.
#:
#: **The cached country is what makes the audit a measurement rather than a
#: sample of Wikidata's availability.** Pinning the item alone was not enough:
#: the audit still had to fetch each pinned item to read its country, roughly a
#: fifth of those requests failed on any given run, and a failed request is
#: indistinguishable from an outlet Wikidata cannot place. Two consecutive runs
#: of identical code returned precision 0.936 and 0.917 for that reason alone.
#: With the answer cached the audit touches the network only when re-pinning, so
#: it returns the same table every time and can be checked offline.
#:
#: ``country`` is the ecosystem the item's country of origin maps to, or ``""``
#: when the item records no country this register recognises — which is a
#: finding, not a gap. A domain absent from this map was never resolved at all.
#: Regenerate with ``scripts/run_register_audit.py --repin``.
PINNED: dict[str, dict[str, str]] = {
    "1prime.ru": {"qid": "Q4376388", "country": "RU", "label": "Prime"},
    "1tv.ru": {"qid": "Q330067", "country": "RU", "label": "Channel One Russia"},
    "7x7-journal.ru": {"qid": "Q104538016", "country": "RU", "label": "7х7"},
    "aif.ru": {"qid": "Q212256", "country": "RU", "label": "Argumenty i Fakty"},
    "apnews.com": {"qid": "Q40469", "country": "WEST", "label": "Associated Press"},
    "axios.com": {"qid": "Q28230873", "country": "WEST", "label": "Axios"},
    "barrons.com": {"qid": "Q4863797", "country": "WEST", "label": "Barron's"},
    "bbc.co.uk": {"qid": "Q9531", "country": "WEST", "label": "British Broadcasting Corporation"},
    "bloomberg.com": {"qid": "Q13975", "country": "WEST", "label": "Bloomberg Television"},
    "businessinsider.com": {"qid": "Q286707", "country": "WEST", "label": "Business Insider"},
    "cnbc.com": {"qid": "Q1023911", "country": "WEST", "label": ""},
    "currenttime.tv": {"qid": "Q55663942", "country": "WEST", "label": "Current Time TV"},
    "dw.com": {"qid": "Q153770", "country": "WEST", "label": "Deutsche Welle"},
    "economist.com": {"qid": "Q180089", "country": "WEST", "label": "The Economist"},
    "faz.net": {"qid": "Q10184", "country": "WEST", "label": "Frankfurter Allgemeine Zeitung"},
    "forbes.com": {"qid": "Q956568", "country": "WEST", "label": "Forbes"},
    "ft.com": {"qid": "Q2196240", "country": "WEST", "label": "FT Magazine"},
    "gazeta.ru": {"qid": "Q595181", "country": "RU", "label": "gazeta.ru"},
    "hromadske.ua": {"qid": "Q15280975", "country": "UA", "label": "Hromadske.TV"},
    "inosmi.ru": {"qid": "Q4201249", "country": "RU", "label": "InoSMI"},
    "iz.ru": {"qid": "Q753932", "country": "RU", "label": "Izvestia"},
    "kommersant.ru": {"qid": "Q1780134", "country": "RU", "label": ""},
    "korrespondent.net": {"qid": "Q1333067", "country": "UA", "label": "Korrespondent"},
    "kp.ru": {"qid": "Q849047", "country": "RU", "label": "Komsomolskaya Pravda"},
    "kyivindependent.com": {"qid": "Q111028947", "country": "UA", "label": "The Kyiv Independent"},
    "kyivpost.com": {"qid": "Q1795015", "country": "UA", "label": "Kyiv Post"},
    "lenta.ru": {"qid": "Q658909", "country": "RU", "label": "lenta.ru"},
    "life.ru": {"qid": "Q4042868", "country": "RU", "label": "Life"},
    "liga.net": {"qid": "Q61366112", "country": "", "label": "ЛІГА.net"},
    "marketwatch.com": {"qid": "Q17068426", "country": "WEST", "label": "MarketWatch"},
    "mediazona.ca": {"qid": "Q28135463", "country": "RU", "label": "MediaZona"},
    "moscowtimes.ru": {"qid": "Q1202611", "country": "WEST", "label": "The Moscow Times"},
    "mskagency.ru": {"qid": "Q94952743", "country": "RU", "label": "Moscow Municipal News Agency"},
    "novayagazeta.eu": {"qid": "Q111654428", "country": "WEST", "label": "Novaya Gazeta Europe"},
    "novayagazeta.ru": {"qid": "Q170135", "country": "RU", "label": "Novaya Gazeta"},
    "npr.org": {"qid": "Q671510", "country": "WEST", "label": "NPR"},
    "nytimes.com": {"qid": "Q9684", "country": "WEST", "label": "The New York Times"},
    "obozrevatel.com": {"qid": "Q4329488", "country": "UA", "label": "OBOZ.UA"},
    "politico.eu": {"qid": "Q991826", "country": "WEST", "label": "Politico Europe"},
    "pravda.com.ua": {"qid": "Q904463", "country": "UA", "label": "Ukrainska Pravda"},
    "rbc.ru": {"qid": "Q629733", "country": "RU", "label": "RBC Information Systems"},
    "regnum.ru": {"qid": "Q1977770", "country": "RU", "label": "REGNUM News Agency"},
    "ren.tv": {"qid": "Q1479649", "country": "RU", "label": "REN TV"},
    "republic.ru": {"qid": "Q4049621", "country": "RU", "label": "Republic.ru"},
    "reuters.com": {"qid": "Q130879", "country": "WEST", "label": "Reuters"},
    "rg.ru": {"qid": "Q1853433", "country": "RU", "label": "Rossiyskaya Gazeta"},
    "riafan.ru": {"qid": "Q48940498", "country": "RU", "label": "Federal News Agency"},
    "rt.com": {"qid": "Q22868", "country": "RU", "label": "RT"},
    "russian.rt.com": {"qid": "Q22868", "country": "RU", "label": "RT"},
    "smotrim.ru": {"qid": "Q211511", "country": "RU", "label": "Russia-1"},
    "spiegel.de": {"qid": "Q131478", "country": "WEST", "label": "Der Spiegel"},
    "sputniknews.com": {"qid": "Q212196", "country": "RU", "label": "Voice of Russia"},
    "strana.news": {"qid": "Q30889269", "country": "UA", "label": "Strana.ua"},
    "svoboda.org": {"qid": "Q120484020", "country": "", "label": "RFE/RL's Russian Service"},
    "tass.ru": {"qid": "Q223799", "country": "RU", "label": "TASS"},
    "telegraph.co.uk": {"qid": "Q7696245", "country": "WEST", "label": "Telegraph Media Group"},
    "theguardian.com": {"qid": "Q11148", "country": "WEST", "label": "The Guardian"},
    "theins.ru": {"qid": "Q48940439", "country": "RU", "label": "The Insider"},
    "themoscowtimes.com": {"qid": "Q1202611", "country": "WEST", "label": "The Moscow Times"},
    "tvrain.ru": {"qid": "Q155172", "country": "RU", "label": "TV Rain"},
    "ukrinform.net": {"qid": "Q987030", "country": "UA", "label": "Ukrinform"},
    "ura.news": {"qid": "Q4476482", "country": "RU", "label": "ura.ru"},
    "vesti.ru": {"qid": "Q628101", "country": "RU", "label": "Russia-24"},
    "vm.ru": {"qid": "Q2614109", "country": "RU", "label": "Vechernyaya Moskva"},
    "vz.ru": {"qid": "Q1970600", "country": "RU", "label": "Vzglyad"},
    "washingtonpost.com": {"qid": "Q166032", "country": "WEST", "label": "The Washington Post"},
    "wsj.com": {"qid": "Q164746", "country": "WEST", "label": "The Wall Street Journal"},
    "zona.media": {"qid": "Q28135463", "country": "RU", "label": "MediaZona"},
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


def _country_from_claims(claims: dict) -> tuple[str | None, str | None]:
    """The ecosystem an item's country of origin implies, present-day first.

    P17 (country) and P495 (country of origin) are both used for media items,
    inconsistently and often only one of the two, so both are read. Within them
    a **present-day state outranks a defunct one**, whatever order Wikidata
    lists them in — an outlet older than 1991 typically carries its whole
    constitutional history, and the first entry is not the informative one.
    """
    seen: list[tuple[str, str]] = []
    for prop in ("P17", "P495"):
        for c in claims.get(prop, []):
            try:
                qid = c["mainsnak"]["datavalue"]["value"]["id"]
            except (KeyError, TypeError):
                continue
            eco = COUNTRY_TO_ECOSYSTEM.get(qid)
            if eco:
                seen.append((qid, eco))
    for qid, eco in seen:
        if qid not in HISTORICAL_COUNTRIES:
            return qid, eco
    return seen[0] if seen else (None, None)


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

    qid_country, eco = _country_from_claims(claims)
    result["wd_country_qid"], result["wd_country_eco"] = qid_country, eco

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
    pinned_only = bool(PINNED)
    rows = []
    for domain, eco in sorted(register.items()):
        pin = PINNED.get(domain)
        if pinned_only:
            # Entirely offline: the pin carries the answer, so nothing here can
            # fail differently between runs.
            if pin is None:
                info = {"domain": domain, "qid": None, "wd_label": None,
                        "wd_country_qid": None, "wd_country_eco": None,
                        "state_owned": None, "identity": "unresolved"}
            else:
                info = {"domain": domain, "qid": pin["qid"],
                        "wd_label": pin.get("label") or None,
                        "wd_country_qid": None,
                        "wd_country_eco": pin.get("country") or None,
                        "state_owned": None, "identity": "website-confirmed"}
        else:
            info = lookup_outlet(domain, pause=pause,
                                 qid_hint=pin["qid"] if pin else None)
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
