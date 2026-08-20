# GDELT Measurement Diagnosis — what the v1 "Ukrainian / Russian / Western sentiment" indicators actually measure

**Date:** 2026-08-17
**Status:** verified empirically this session (reproducible via
`thesis_v2/scripts/diagnose_gdelt_streams.py`)
**Why this document exists:** it answers supervisor comment #3 ("you should
provide a much more detailed description of the methodology used to identify
Western, Ukrainian, and Russian sentiment in the GDELT data") and, in the
process, identifies what is probably the single largest reason the v1 results
were insignificant.

---

## 1. Bottom line

The v1 pipeline downloaded from **`http://data.gdeltproject.org/gkg/`** — the
**GKG 1.0 daily stream, which is effectively English-language only**. It then
assigned each article to `ukrainian` / `russian` / `western` / `other` using, for
88.6% of articles, the **most-mentioned country in the article's `LOCATIONS`
field** (`docs/v1/phase3_classification_audit.md` §2.2, §7.3).

That is a **topic** classifier, not a **source-perspective** classifier.

So the v1 indicators are, to a first approximation:

| Label in v1 | What it actually measures |
|---|---|
| "Ukrainian sentiment" | tone of *(mostly Anglophone)* articles whose dominant location mention is Ukraine |
| "Russian sentiment" | tone of *(mostly Anglophone)* articles whose dominant location mention is Russia |
| "Western sentiment" | tone of *(mostly Anglophone)* articles whose dominant location mention is a Western country |

These three series are all built from broadly the *same* media population and
differ only by which country the article is *about*. They are therefore expected
to be (a) highly collinear with each other, (b) highly collinear with overall
war-news tone and volume, and (c) nearly uninformative about cross-national
*differences in perception* — which is the thesis's stated novelty.

The v1 "narrative gap" features (`narrative_gap_ua_west`, etc.) are differences
between two topic-conditioned tone series, not between two national media
ecosystems. It is unsurprising that they never entered the SHAP top-10
(`docs/v1/phase7_audit.md` §5, "H3 verdict: NOT supported").

**The v1 audit already contains the admission, in a footnote:**

> "The `primary_country` field in `domain_to_country.csv` is the **most-mentioned
> country in editorial coverage**, not the country of publication. A Ukrainian
> outlet covering the Russia–Ukraine war will have `primary_country = RS` because
> Russia is mentioned in most of its articles."
> — `docs/v1/phase3_gdelt_audit.md` §9.2

The reported per-group "precision" of 0.365 (Ukrainian) and 0.318 (Russian)
was explained away as an artefact of the validation proxy. The measurements
below suggest the more likely reading: those groups genuinely do not contain
Ukrainian and Russian media.

---

## 2. Evidence

Three GDELT streams were sampled on the same three dates. Counts for the v2
streams are for a single 15-minute slice (12:00:00 UTC); the v1 stream is a
full day.

### 2.1 Stream used by v1 — `data.gdeltproject.org/gkg/` (GKG 1.0 daily, full day)

| Date | records | unique domains | top TLDs | `.ru` articles | `.ua` articles |
|---|---|---|---|---|---|
| 2016-03-01 | 163,816 | 13,460 | com, au, uk, org, net, ca | **16** | **86** |
| 2020-03-01 | 51,455 | 6,685 | com, uk, au, org, net, ca | **4** | **4** |
| 2025-03-01 | 60,690 | 5,361 | com, uk, au, org, net, ca | **7** | **21** |

There is **no language field at all** in GKG 1.0, and Russian/Ukrainian outlets
are present at the level of single-digit-to-tens of articles per day out of
~60,000. Russian- and Ukrainian-media sentiment cannot be measured from this
stream.

### 2.2 GKG 2.0 English stream — `gdeltv2/*.gkg.csv.zip` (15-min slice)

| Date | records | `.ru` | `.ua` | source languages |
|---|---|---|---|---|
| 2016-03-01 | 3,044 | 0 | 0 | 100% native English |
| 2022-03-01 | 1,468 | 0 | 0 | 100% native English |
| 2025-03-01 | 767 | 0 | 1 | 100% native English |

Also English-only. Not a fix.

### 2.3 GKG 2.0 **TRANSLINGUAL** stream — `gdeltv2/*.translation.gkg.csv.zip` (15-min slice)

| Date | records | `.ru` arts (domains) | `.ua` arts (domains) | `srclc=rus` | `srclc=ukr` | top source languages |
|---|---|---|---|---|---|---|
| 2016-03-01 | 8,137 | **380** (36) | **157** (39) | 688 | 94 | spa, tur, ara, **rus**, zho, deu, fra, ita |
| 2022-03-01 | 3,380 | **154** (18) | **71** (12) | 292 | 18 | zho, fra, **rus**, deu, spa, ita, vie, pol |
| 2025-03-01 | 2,613 | **131** (19) | **29** (8) | 198 | 38 | ita, deu, tur, spa, **rus**, fra, ara, zho |

Sample outlets actually present: `tass.ru`, `ria.ru`, `mk.ru`, `pravda.ru`,
`regnum.ru`, `grani.ru`, `newtimes.ru` — and `unian.ua`, `pravda.com.ua`,
`tsn.ua`, `nv.ua`, `eurointegration.com.ua`, `day.kyiv.ua`.

Scaling the 15-minute slice by 96 files/day gives roughly **1.2×10⁴ `.ru`
articles/day** and **~1.9×10⁴ Russian-language articles/day** in 2025, against
**7 `.ru` articles/day** in the stream v1 used — a difference of roughly three
orders of magnitude.

### 2.4 Availability and size of the translingual archive

From `data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt`
(downloaded 2026-08-17):

- First file: `20150218224500.translation.gkg.csv.zip`
- Last file: `20260817170000.translation.gkg.csv.zip`
- **390,440** translingual GKG files, **4.19 TB** compressed in total
- Continuous coverage **2015-02-18 → present**, 15-minute granularity, 65+ source
  languages with an explicit `srclc:` source-language code

---

## 3. Consequences

### 3.1 It explains the insignificance, partly

Three near-collinear topic-tone series cannot deliver incremental predictive
content over each other or over VIX and a war-regime trend. The v1 horse race
(F ⊂ P ⊂ N ⊂ PN ⊂ PNG) was, on the news side, adding noise-differentiated copies
of the same variable. The flat MAE across information sets in
`docs/v1/phase7_audit.md` §3 is the expected signature of that.

### 3.2 It is the reason comment #3 is hard to answer as things stand

An honest, detailed methodology section for the current indicators would have to
say: *"national sentiment groups are assigned by the country most frequently
mentioned in the article, using an English-language corpus."* That will not
survive a reader who knows the GDELT literature.

### 3.3 It is also the opportunity

Fixing it does three things at once:

1. **Extends the sample by 7.6 years** (2015-02 → 2026), which is exactly
   supervisor comment #1.
2. **Creates genuinely independent indicators** — Russian-language state media,
   Russian-language independent media, Ukrainian media, Western media are
   distinct populations with distinct information sets and incentives, so their
   tone series carry different information. That is what the thesis always
   claimed to measure.
3. **Aligns the thesis directly with the paper the supervisor asked to be
   cited.** Bondarenko, Lewis, Rottner & Schüler (2024, *JIE* 152:104005) find
   precisely that geopolitical-risk shocks identified from **local-language**
   Russian news have significant adverse macroeconomic effects while shocks
   identified from **English-language** news do not, and they split
   state-controlled from independent media. Our v1 indicators are, in their
   terminology, all on the English side of that comparison — the side they show
   has no effect.

---

## 4. What to build instead (summary; full spec in `research_plan_v3.md` §5)

Classify each article by **who published it**, not what it mentions:

| Tier | Signal | Source |
|---|---|---|
| 1 | Curated outlet register (top ~300 outlets by volume, hand-verified: country, language, state-controlled vs independent) | manual, auditable, citable |
| 2 | Source language (`srclc` from V2.1 TranslationInfo) | GDELT, exact |
| 3 | Domain ccTLD (`.ua`, `.ru`, `.de`, …) | exact |
| 4 | GDELT `SourceCommonName` → country via GDELT's own domain-country lookup | GDELT |

Language and country must be used **jointly, not interchangeably**: a large share
of Ukrainian outlets publish in Russian, so `srclc=rus` alone would misclassify
Ukrainian media as Russian. The register (tier 1) resolves this for the outlets
that carry most of the volume, and the fallback tiers cover the tail with a
documented, measurable error rate.

Validation must be a genuine hand-labelled precision audit on a stratified
sample (the v1 "automated agreement check" validated the classifier against a
proxy built from the same flawed signal, so it could not detect this problem).

---

## 5. Reproducing this diagnosis

```bash
python thesis_v2/scripts/diagnose_gdelt_streams.py --dates 20160301 20220301 20250301
```

No credentials required; ~100 MB of downloads.
