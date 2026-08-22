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
Section 8.4 reports what this costs.

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
daily attention changes reach a maximum of 0.673, between WEST and EN_GLOBAL,
which overlap by construction. Every other pair is far lower: Ukrainian against
native-English **0.05**, Russian state against native-English 0.05, Ukrainian
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
18.8% to 40.7% for Western media and from 11.8% to 23.8% for native-English
media. Ukrainian and Russian outlets, already above 84%, rise to 91–96%.

**What was not done.** The hand-labelled precision audit specified in the
research design — several hundred articles opened and classified by a reader —
was not carried out. The validation above is therefore incomplete, and the
classification is provisional. Section 8.3 reports a register error found by a
robustness run rather than by validation, which is the concrete argument for
completing the audit before these indices are used again.
