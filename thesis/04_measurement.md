# Chapter 4 — Measuring geopolitical risk perceptions

This chapter describes how the perception indices are built. It is longer than a
data appendix would be, for two reasons. The first is that the supervisor's
review asked for a fuller description of how Western, Ukrainian and Russian
sentiment were identified. The second is that writing that description honestly
was impossible for the previous version of these indicators, because the method
did not measure what it claimed. Establishing what went wrong, and what replaces
it, is therefore part of the contribution rather than preliminary to it.

## 4.1 What the previous indicators measured

The earlier version of this project built its national sentiment series from
GDELT's Global Knowledge Graph, downloading from the version 1.0 daily stream.
Two properties of that pipeline, neither documented at the time, determine what
the resulting series contain.

**The stream is effectively English-only.** Sampling the same three dates across
all available GDELT streams shows the scale of the problem. On 1 March 2025 the
GKG 1.0 daily file contains 60,690 records, of which **7 carry a `.ru` domain and
21 a `.ua` domain**. On 1 March 2020 the counts are four and four. There is no
source-language field in GKG 1.0 at all.

**Nationality was assigned by topic, not by publisher.** For 88.6% of articles,
the national group was set by the most-mentioned country in the article's
`LOCATIONS` field. An article in an American newspaper about Russian troop
movements is therefore classified as Russian.

Together these mean the three series labelled Ukrainian, Russian and Western
sentiment were, to a first approximation, the tone of English-language articles
about Ukraine, about Russia, and about Western countries. They are drawn from one
media population and differ only in subject. That they were mutually collinear,
and that their differences carried no information about anything, follows from
the construction rather than from any fact about the world.

The earlier audit recorded the symptom without drawing the conclusion, reporting
per-group precision of 0.365 for the Ukrainian group and 0.318 for the Russian
group and attributing it to the validation proxy. The simpler reading is that
those groups did not contain Ukrainian or Russian media.

## 4.2 The corpus

The replacement is built from the **GDELT 2.0 Translingual** archive, which
processes material in 65 source languages, machine-translates it, and applies the
same annotation pipeline to the translated text. It begins on 18 February 2015
and is continuous since. Accessed through BigQuery's `gdelt-bq.gdeltv2.
gkg_partitioned` table — 1.83 billion rows, 21.8 TB, partitioned by day.

The difference in coverage is not marginal. On the same day for which GKG 1.0
yields seven Russian-domain articles, the translingual archive carries roughly
9,700 Russian-language and 3,200 Ukrainian-language records. Coverage is present
from the first days of the archive: 18,109 Russian-language and 3,685
Ukrainian-language records on 19 February 2015.

An article enters the sample if it geolocates to Ukraine or Russia, identified by
the FIPS country codes `UP` and `RS` in the version 1 `Locations` field. This is
a coarse filter and will admit coverage that mentions either country
incidentally. It was chosen over the richer `V2Themes` field because the two are
priced very differently by BigQuery — 0.242 TB against 1.853 TB across the full
sample — and the coarser filter kept the entire ingest inside the free tier.
Section 8.7 reports what this costs.

## 4.3 Assigning articles to media ecosystems

Each article is assigned to the ecosystem of **the outlet that published it**,
using four tiers applied in order: a hand-curated register of high-volume
outlets; the domain's country-code top-level domain; source language conditioned
on country; and GDELT's own domain-to-country lookup.

**Country dominates language at every tier.** This is the single most important
rule in the chapter and it is not a technicality. Measured on the corpus itself,
Ukrainian outlets publish heavily in Russian: `24tv.ua` appears with 2,595
Ukrainian-language and 1,865 Russian-language articles; `gazeta.ua` with 1,739
and 1,648; `censor.net.ua`, `nv.ua` and `segodnya.ua` are Russian-language
almost throughout. A rule that assigned nationality from source language would
place a large share of Ukrainian media in the Russian ecosystem. The two series
would then move together, and that agreement — entirely an artefact — would be
indistinguishable from the finding that the two national narratives converge.

Six ecosystems are carried forward. **UA** is Ukrainian outlets in both language
variants. **RU_STATE** is Russian outlets under state ownership or control.
**RU_INDEP** is Russian-language independent and exile media, the press-freedom
control that Bondarenko et al. (2024) apply. **RU_OTHER** is Russian media
outside the register, reported so that unclassified volume is visible rather than
hidden. **WEST** is outlets in NATO and EU countries. **EN_GLOBAL** is
native-English material regardless of country, which reproduces the information
set the previous version of this project was working with.

Syndication platforms — `msn.com`, `yahoo.com`, `news.google.com` and similar —
are excluded from every ecosystem. They carry large volume and no editorial
voice, and counting them as Western media would measure redistribution rather
than perspective.

## 4.4 The indices

Two series per ecosystem per day, both computed server-side so that only daily
aggregates leave BigQuery.

**Attention** is the share of that ecosystem's own daily output that is
conflict-related. **Tone** is the mean GDELT tone of its conflict articles.

Attention is a share and never a raw count. GDELT's source coverage drifts
substantially over eleven years — the same sampled calendar day yields 546,301
records in 2015, 836,905 in 2016 and 316,244 in 2026 — and a raw-count series
would show that drift as a trend in every ecosystem simultaneously.

The resulting attention levels differ enormously by ecosystem and are themselves
descriptive of the media environments: conflict coverage is 79.2% of Ukrainian
outlets' total output across the sample, 71.4% of Russian state media's, and
6.6% of Western media's.

For the anticipation analysis of Chapter 6, each ecosystem's conflict coverage is
further split into **realized** and **anticipatory** shares using GDELT's theme
taxonomy — `KILL`, `ARMEDCONFLICT`, `TERROR` and related codes against
`THREATEN`, `MILITARY`, `BORDER`, `NUCLEAR` and related. Because GDELT applies
one classifier to the translated text of all 65 languages, this split is
comparable across ecosystems by construction. That is a real advantage over
building a threat/act dictionary per language, which would have required
validating cross-language equivalence by hand. The cost is that the taxonomy is
GDELT's rather than one designed for this purpose; the mapping is an
interpretation and was fixed in advance of any test.

## 4.5 Validation

The previous version's validation could not detect its own error, because it
checked the classifier against a proxy built from the same flawed signal.
The checks here are therefore deliberately external.

**Mutual independence.** If the ecosystems were near-duplicates, as the previous
series were, nothing downstream could distinguish them. Pairwise correlations of
daily attention changes reach a maximum of 0.602, between WEST and EN_GLOBAL,
which overlap by construction. Every other pair is far lower: Ukrainian against
native-English **0.02**, Russian state against native-English 0.06, Ukrainian
against Western 0.18, Ukrainian against Russian state 0.44. These are distinct
populations.

**Agreement with a published index.** The Western index should track the
Caldara–Iacoviello geopolitical risk index, which no one here constructed. In
levels, over the window in which GPR is driven by the Russia–Ukraine conflict,
the correlation is **0.866** for WEST and **0.884** for EN_GLOBAL. Over 2017–2019,
when GPR is driven by North Korea and Iran, it falls to 0.083 and 0.048 — the
correct behaviour for an index specific to a different conflict, and a useful
demonstration that the series are measuring what they claim rather than tracking
general news volume.

The same correlations computed on daily *changes* are near zero throughout. Two
measures of the same conflict, agreeing at 0.87 in levels, share almost nothing
day to day. This is reported rather than buried: it means daily attention
movements are dominated by noise, and it motivates the weekly specifications in
Chapter 6.

**Behaviour on a known date.** Attention share on 24 February 2022 rises from
19.0% to 40.9% for Western media and from 11.8% to 23.8% for native-English
media. Ukrainian and Russian outlets, already above 84%, rise to 91–96%.

**Sensitivity to the classification rule.** The three checks above ask whether
the indices measure something real. This one asks a different and sharper
question: whether the answer in Chapter 6 depends on the classification choices
that produced them. Every one of those choices was a judgement — which tier
applies first, whether to infer a country from a top-level domain, whether to
fall back on language at all, whether syndication platforms count as media — and
a reader is entitled to ask what happens if they are made differently.

Four alternative rules are run against the shipped one, and Gate 2's entire grid
is re-estimated under each:

| rule | what it changes | blocks it produces |
|---|---|---|
| baseline | — | UA, RU_STATE, RU_INDEP, WEST, EN_GLOBAL |
| `register_only` | drops both inferred tiers; only registered domains classify | four (no EN_GLOBAL) |
| `no_language_tier` | drops the language fallback, the weakest link | four (no EN_GLOBAL) |
| `language_first` | assigns by language **before** country | four (no RU_INDEP) |
| `with_aggregators` | puts msn.com and the other platforms back | five |

Under the primary alignment, the number of cells surviving correction is **1
under the baseline and between 1 and 2 under every alternative**, out of 31. The
null does not depend on how outlets were classified.

Two details in that table are worth reading rather than skipping. `register_only`
produces no native-English block at all, because EN_GLOBAL *is* the language
fallback — so that row is the null surviving even when the control block is cut
from two ecosystems to one. And `language_first` produces no Russian-independent
block, because Russian-language articles from independent outlets are claimed by
the language tier before the register is ever consulted. That is the concrete
cost of the rule §4.3 rejects: it does not merely misassign some outlets, it
makes the state-versus-independent distinction unrepresentable. The rejection was
a design decision made in advance; this is the measurement of what it bought.

Running this the obvious way would have meant one full ingest per rule. It did
not need to: the rules differ in how they label an article, not in which articles
they read, so a single scan labels each article five ways. The whole analysis
cost what one ingest costs.

**What the precision audit does and does not establish.** The research design
specified a hand-labelled audit — several hundred articles opened and classified
by a reader in Russian and Ukrainian — and that was never carried out. What
replaces it is described in §4.6, and it is neither a substitute for reading
articles nor as weak as that framing suggests.

## 4.6 The precision audit, automated

The research design specified a hand-labelled precision audit: several hundred
articles opened and classified by a reader in Russian and Ukrainian, with a
confusion matrix per tier. It was never carried out, and for most of this
project's life it was the largest stated limitation. What follows is not that
audit. It is a different one, and the case for why it substitutes is worth making
carefully rather than asserting.

**The classifier is a deterministic function of the domain.** Two articles from
the same outlet on the same day receive the same label, always. Article-level
precision is therefore domain-level precision weighted by article volume, and
sampling articles reveals nothing that the domain assignments do not already
contain — *provided* those assignments can be checked against something outside
this project. Auditing the domains is not a weaker version of auditing articles;
it is the same quantity computed exactly rather than estimated from a sample.

Wikidata is that external source. It is maintained independently of GDELT and of
this thesis, and it records the property the register claims: an outlet's country
of origin.

**Identity is established by the outlet's own website, not by its name.** This is
the detail that makes the audit a measurement, and it was learned the hard way.
An earlier version took the best-matching Wikidata item by name search, and that
is not stable: across two runs of identical code `dw.com` resolved once to
Deutsche Welle and once to *Der Westen*, an unrelated German regional paper.
Every candidate item is now accepted only if its **official-website property**
resolves to the registered domain, every candidate is examined rather than the
first plausible one, and the confirmed identities are pinned to a committed map
together with what they say. The audit consequently touches the network only when
that map is rebuilt: it runs offline, in under a second, and returns a
byte-identical table every time.

| ecosystem | outlets | verifiable | agree | disagree | precision |
|---|---|---|---|---|---|
| Russian state | 28 | 23 | 23 | 0 | **1.000** |
| Western | 28 | 23 | 23 | 0 | **1.000** |
| Russian independent | 16 | 12 | 9 | 3 | 0.750 |
| Ukrainian | 12 | 8 | 8 | 0 | **1.000** |

Across the register, **44 of 66 verifiable outlets agree — precision 0.955**.
The eighteen remaining outlets have no Wikidata item whose website resolves to
the registered domain, or an item that records no country; they are reported as
unverifiable and counted neither way, since an audit that dropped them silently
would overstate its precision and one that assumed them correct would overstate
its coverage.

**Every one of the three disagreements is an exile newsroom**, and they are the
same disagreement three times over:

| domain | register says | Wikidata item | Wikidata country |
|---|---|---|---|
| `moscowtimes.ru` | Russian independent | The Moscow Times | Western |
| `themoscowtimes.com` | Russian independent | The Moscow Times | Western |
| `novayagazeta.eu` | Russian independent | Novaya Gazeta Europe | Western |

This is the rule of §4.3 meeting the limit of the source rather than an error in
either. Wikidata's country of origin is a *legal* fact — where an outlet is
registered — and after 2022 these newsrooms are registered in Amsterdam and Riga.
The register places them by whose perception they carry, which is Russian: they
are Russian journalists reporting in Russian for a Russian readership. The
disagreement is adjudicated in the decision log and deliberately not acted on,
because acting on it would empty the independent Russian block of precisely the
outlets that define it.

The three blocks that carry the thesis's live claims — Russian state, Western and
Ukrainian — return no disagreement at all.

**What the audit found that validation had not.** It earned its place on the
first run. `svoboda.org` — Radio Free Europe/Radio Liberty's Russian service,
funded by the US Agency for Global Media — was sitting in the Russian
*independent* register, which is the Deutsche Welle error of §8.3 repeated
exactly. Both moved, under a rule now stated where it is applied. The audit found
by validation what the earlier error had been found by luck.

**Three limits, stated rather than blurred.**

*It validates domains, not attribution.* Every check here establishes that a
registered domain belongs to the country the register assigns it. None
establishes that GDELT filed a given article under the right domain. If
`SourceCommonName` is wrong for some fraction of articles, every result in this
thesis inherits that error and nothing here would see it. That is the residual
gap a reader with the languages would close, and it is narrower and better
specified than the one the design began with.

*Correctness was bought with coverage.* Requiring an item's own website to
confirm the domain rejects the plausible-looking match, and sixteen outlets have
no item that clears that bar. Two more — including `svoboda.org` itself — are
confirmed but carry no country Wikidata will state, so they are identified and
still unverifiable.

*Ownership is not audited.* Wikidata records ownership far more sparsely than
country, too sparsely to validate the state-versus-independent split. That
dimension carries the one contrast this thesis has already retracted as
underpowered (§8.3), and the audit neither rescues nor further damages it.

