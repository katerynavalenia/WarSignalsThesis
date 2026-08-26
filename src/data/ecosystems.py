"""Assigning each article to a media ecosystem by **publisher**, not by topic.

v1's fatal error was classifying by the country an article *mentions*
(``docs/v3/gdelt_measurement_diagnosis.md``). This module classifies by who
published it, using the tier order of ``research_plan_v3.md`` §5.2: a curated
register first, then ccTLD, then source language conditioned on country.

**Country dominates language, always.** Measured on the BigQuery corpus,
Ukrainian outlets publish heavily in Russian — ``24tv.ua`` appears with 2,595
Ukrainian-language and 1,865 Russian-language articles, and ``censor.net.ua``,
``nv.ua`` and ``segodnya.ua`` are Russian-language almost throughout. A
``srclc='rus'`` rule would file all of them under Russian media, which would
manufacture agreement between the two ecosystems and destroy the result the
thesis is trying to measure. Language is therefore only ever used to split
*within* a country.

The state/independent split for Russian media follows Bondarenko et al. (2024),
who control for press freedom the same way. It is the most contestable part of
the register and is marked as such: several outlets changed ownership or were
shut down inside the sample window, and `PROVISIONAL` flags those.
"""

from __future__ import annotations

# --- Tier 1: curated register -------------------------------------------------

#: Russian outlets that are state-owned, state-founded, or under state control
#: for most of the sample.
RU_STATE = {
    "tass.ru", "special.tass.ru", "ria.ru", "rg.ru", "rt.com", "riafan.ru",
    "vesti.ru", "iz.ru", "vz.ru", "life.ru", "1tv.ru", "tvzvezda.ru",
    "smotrim.ru", "sputniknews.com", "ren.tv", "1prime.ru", "mskagency.ru",
    "aif.ru", "kp.ru", "pda.kp.ru", "vm.ru", "regnum.ru", "lenta.ru",
    "gazeta.ru", "ura.news", "russian.rt.com", "inosmi.ru", "rueconomics.ru",
}

#: Russian-language outlets that are independent, exiled, or foreign-funded.
#: PROVISIONAL: echo.msk.ru was liquidated in March 2022; kommersant, vedomosti
#: and rbc are business titles whose editorial independence narrowed over the
#: sample rather than switching on a single date.
RU_INDEPENDENT = {
    "meduza.io", "novayagazeta.eu", "novayagazeta.ru", "theins.ru",
    "zona.media", "mediazona.ca",
    "moscowtimes.ru", "themoscowtimes.com", "republic.ru", "tvrain.ru",
    "echo.msk.ru", "kommersant.ru", "vedomosti.ru", "rbc.ru", "znak.com",
    "7x7-journal.ru",
}
# NOTE: ``svoboda.org`` and ``currenttime.tv`` were also in this set and have
# been moved to :data:`WEST_REGISTER` for the same reason as ``dw.com`` below.
# Both are Radio Free Europe/Radio Liberty services, funded by the US Agency for
# Global Media. A state-funded external broadcaster classifies to the state that
# funds it, whatever language it publishes in; that is the single rule that puts
# Deutsche Welle in Germany and RFE/RL in the United States.
#
# ``svoboda.org`` was flagged by the Wikidata audit, which is how the error was
# found. What the audit reports for it has since changed, and the change is worth
# recording rather than papering over: the flag came from a version that matched
# items by name, and the stricter resolver now in use confirms a *different*
# item for the domain — Q120484020, "RFE/RL's Russian Service" — which records no
# country at all. The identity is confirmed and the country is not, so the audit
# now returns it as unverifiable rather than as a disagreement.
#
# The correction therefore rests on the rule and on what RFE/RL is, not on a flag
# that no longer reproduces. ``currenttime.tv`` is the same organisation and
# resolves cleanly (Q55663942, United States), which is the evidence the other
# one lacks.
#
# The rule cuts the other way for **exile newsrooms**, which stay with their
# country of origin: Meduza, Novaya Gazeta Europe, TV Rain and The Moscow Times
# are Russian newsrooms reporting for a Russian audience from abroad, and
# Wikidata's country of origin for them records legal domicile (Latvia,
# Netherlands) rather than editorial perspective. The audit's Meduza flag is
# therefore adjudicated and dismissed, not acted on.
#
# NOTE: ``dw.com`` was in this set for the 2026-08-20 ingest and should not have
# been. Deutsche Welle is a German public broadcaster with a Russian-language
# service — a Western outlet by publisher, which is the criterion this module
# exists to apply. It is the single largest contributor to RU_INDEP volume and
# carries the largest negative tone shift (−0.73), so it inflates that
# ecosystem's measured reaction to the invasion. It now classifies as WEST via
# :data:`WEST_REGISTER`. The committed ecosystem tables predate the fix; see
# ``docs/v3/gate3_results.md``. This is exactly the error class the hand-labelled
# precision audit exists to catch, found instead by a fixed-panel robustness run.

#: Ukrainian outlets that do not carry a .ua domain.
UA_REGISTER = {
    "unian.net", "censor.net", "pravda.com.ua", "ukrinform.net",
    "kyivindependent.com", "kyivpost.com", "epravda.com.ua", "hromadske.ua",
    "liga.net", "obozrevatel.com", "korrespondent.net", "strana.news",
}

#: Investor-facing Western outlets on generic TLDs. Deliberately *excludes*
#: aggregators (msn.com, yahoo.com, news.google.com, iheart.com), which carry
#: large volume but no editorial voice — counting them as Western media would
#: measure syndication, not perspective.
WEST_REGISTER = {
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "nytimes.com",
    "washingtonpost.com", "cnn.com", "bbc.co.uk", "bbc.com", "theguardian.com",
    "telegraph.co.uk", "economist.com", "apnews.com", "cnbc.com", "politico.eu",
    "spiegel.de", "lemonde.fr", "faz.net", "handelsblatt.com", "marketwatch.com",
    "barrons.com", "forbes.com", "businessinsider.com", "axios.com", "npr.org",
    "dw.com", "svoboda.org", "currenttime.tv",
}

#: Excluded from every ecosystem: syndication platforms with no newsroom.
AGGREGATORS = {
    "msn.com", "yahoo.com", "news.yahoo.com", "news.google.com", "iheart.com",
    "finance.yahoo.com", "news.mail.ru", "news.meta.ua", "flipboard.com",
    "newsbreak.com", "smartnews.com",
}

# --- Tier 2: country top-level domains ---------------------------------------

#: NATO/EU member ccTLDs — the investor-facing information set.
WEST_TLDS = {
    "us", "uk", "de", "fr", "it", "es", "pl", "nl", "se", "no", "dk", "fi",
    "ca", "au", "be", "at", "cz", "pt", "ie", "gr", "ro", "hu", "sk", "si",
    "lt", "lv", "ee", "bg", "hr", "lu", "is", "nz", "ch",
}


def build_case_sql(domain: str = "SourceCommonName", srclc_expr: str = "srclc") -> str:
    """SQL CASE assigning one ecosystem per article, tiers applied in order.

    Emitted as SQL rather than applied in pandas because the classification has
    to happen server-side — the whole point of the BigQuery route is that only
    daily aggregates cross the wire.
    """

    def lit(items) -> str:
        return ", ".join(f"'{d}'" for d in sorted(items))

    return f"""
    CASE
      -- Tier 0: aggregators carry volume but no editorial voice.
      WHEN {domain} IN ({lit(AGGREGATORS)}) THEN 'AGGREGATOR'

      -- Tier 1: curated register. Country before language, throughout.
      WHEN {domain} IN ({lit(UA_REGISTER)}) THEN 'UA'
      WHEN {domain} IN ({lit(RU_STATE)}) THEN 'RU_STATE'
      WHEN {domain} IN ({lit(RU_INDEPENDENT)}) THEN 'RU_INDEP'
      WHEN {domain} IN ({lit(WEST_REGISTER)}) THEN 'WEST'

      -- Tier 2: ccTLD. A .ua outlet is Ukrainian whatever language it uses.
      WHEN ENDS_WITH({domain}, '.ua') THEN 'UA'
      WHEN ENDS_WITH({domain}, '.ru') THEN 'RU_OTHER'
      WHEN REGEXP_EXTRACT({domain}, r'\\.([a-z]+)$') IN ({lit(WEST_TLDS)}) THEN 'WEST'

      -- Tier 3: language, only where country is unknown. Generic TLDs with no
      -- translation record are overwhelmingly Anglophone newsrooms.
      WHEN {srclc_expr} IS NULL THEN 'EN_GLOBAL'
      WHEN {srclc_expr} = 'ukr' THEN 'UA'
      WHEN {srclc_expr} = 'rus' THEN 'RU_OTHER'
      ELSE 'OTHER'
    END
    """


def build_variant_case_sql(variant: str, domain: str = "SourceCommonName",
                           srclc_expr: str = "srclc") -> str:
    """The classifier under an alternative rule, for the sensitivity analysis.

    The research design promised a sensitivity analysis across classification
    rules, and this is the machinery for it. Each variant removes or reverses one
    decision in :func:`build_case_sql`, so the question "does the answer depend on
    how outlets were classified" can be answered by re-running the gates rather
    than argued.

    ``baseline``
        The shipped classifier, unchanged.
    ``register_only``
        Tier 1 only. Everything not explicitly registered becomes ``OTHER``,
        which tests whether the ccTLD and language tiers carry any result.
    ``no_language_tier``
        Tiers 0-2. Drops the language fallback for generic TLDs, the weakest
        inference in the chain.
    ``language_first``
        Language *before* country — the rule this module exists to reject. If
        the answer changes here and nowhere else, the rejected rule is doing the
        work, which is exactly what a reader should want to know.
    ``with_aggregators``
        Puts msn.com and friends back in, by country of TLD. Tests whether
        excluding syndication platforms changes anything.
    """

    def lit(items) -> str:
        return ", ".join(f"'{d}'" for d in sorted(items))

    agg = f"WHEN {domain} IN ({lit(AGGREGATORS)}) THEN 'AGGREGATOR'"
    register = f"""
      WHEN {domain} IN ({lit(UA_REGISTER)}) THEN 'UA'
      WHEN {domain} IN ({lit(RU_STATE)}) THEN 'RU_STATE'
      WHEN {domain} IN ({lit(RU_INDEPENDENT)}) THEN 'RU_INDEP'
      WHEN {domain} IN ({lit(WEST_REGISTER)}) THEN 'WEST'"""
    cctld = f"""
      WHEN ENDS_WITH({domain}, '.ua') THEN 'UA'
      WHEN ENDS_WITH({domain}, '.ru') THEN 'RU_OTHER'
      WHEN REGEXP_EXTRACT({domain}, r'\\.([a-z]+)$') IN ({lit(WEST_TLDS)}) THEN 'WEST'"""
    language = f"""
      WHEN {srclc_expr} IS NULL THEN 'EN_GLOBAL'
      WHEN {srclc_expr} = 'ukr' THEN 'UA'
      WHEN {srclc_expr} = 'rus' THEN 'RU_OTHER'"""

    if variant == "baseline":
        body = agg + register + cctld + language
    elif variant == "register_only":
        body = agg + register
    elif variant == "no_language_tier":
        body = agg + register + cctld
    elif variant == "language_first":
        body = agg + language + register + cctld
    elif variant == "with_aggregators":
        body = register + cctld + language
    else:
        raise ValueError(f"unknown variant: {variant}")

    return f"CASE\n      {body}\n      ELSE 'OTHER'\n    END"


#: The rules the sensitivity analysis compares. ``baseline`` must stay first.
CLASSIFIER_VARIANTS = (
    "baseline", "register_only", "no_language_tier", "language_first",
    "with_aggregators",
)


#: Ecosystems carried into the analysis. RU_OTHER is Russian media outside the
#: register — kept separate so the state/independent split stays clean, and
#: reported so unclassified Russian volume is visible rather than hidden.
ECOSYSTEMS = ("UA", "RU_STATE", "RU_INDEP", "RU_OTHER", "WEST", "EN_GLOBAL", "OTHER")

#: The arm that reproduces v1's information set, and the one Bondarenko et al.
#: find inert for Russian macro aggregates.
ENGLISH_ARM = "EN_GLOBAL"
