# Chapter 3 — Data

This chapter describes what was collected, over what window, and how the pieces
were assembled into the sample the rest of the thesis uses. It also records two
things that a data chapter usually omits: a validation exercise whose candidates
all failed, reported as it came out, and a set of data that no longer exists and
therefore closes off one of the research questions the design originally asked.

The organising fact is the sample window. The previous version of this project
ran on 29 September 2022 onward, a start date inherited from the Ukrainian
air-attack series it merged against rather than from anything about the news
data. That window excludes the entire build-up and the February-2022 re-rating —
the single largest identifying event available — and it was the first item in the
supervisor's review. Extending it is the reason the news and equity spines below
were re-acquired rather than reused; only the two Bloomberg index series carry
over from the earlier phases.

## 3.1 The binding constraint

The sample begins on **18 February 2015** because that is when GDELT's
translingual archive begins. Nothing else in the design binds earlier: the
geopolitical risk index runs from 1985, the FRED controls run from well before
2015, and every equity series used here has listing history reaching back
further. The perception indices are the scarce input, so their first day is the
sample's first day.

That takes the study from the 931 trading days of the attrition phase to 2,837 —
and, more importantly than the count, it places the pre-war period, the build-up, the
invasion and the attrition phase inside one sample rather than leaving three of
the four outside it.

## 3.2 The news corpus

The perception indices are built from the **GDELT 2.0 Translingual** Global
Knowledge Graph: 390,440 files and 4.19 TB compressed over the full archive.
Chapter 4 explains why the previous version's English-only stream could not
support the question and how publishers are assigned to ecosystems; this section
covers acquisition and coverage only.

The archive is queried through BigQuery rather than downloaded. The table
`gdelt-bq.gdeltv2.gkg_partitioned` holds **1.83 billion rows across 21.8 TB** and
is partitioned by day, which is what makes the ingest affordable: a query
restricted to a date range scans only those partitions, and all aggregation
happens server-side so that only daily ecosystem-level series leave the warehouse.

Two coverage figures matter and they are not the same number.

**What exists.** The perception indices as built cover **18 February 2015 to
20 May 2026 — 4,027 days, 98% of the calendar**, the missing days being gaps in
GDELT's own archive rather than a filtering choice. On matched units that is
about three times the sample the supervisor reviewed: 2,837 trading days against
931, or 4,027 calendar days against 1,370.

**What each test ran on.** The perception indices cover **4,027 days**, split
deliberately into **3,073 in-sample days** and a **954-day held-out block** that
no in-sample estimate touches. Every test uses the whole of what is available to
it:

| test | days available to it | note |
|---|---|---|
| Gates 1–2 | 3,073 in-sample | ~2,104 trading-day observations pooled |
| Gate 3 | **4,027** | 2,754 daily observations in the pooled cell |
| Gate 4 | continuous 2021-06 → 2023-12 | the gas crisis, ingested continuously |
| Gate 5 | 954 held out | never used in-sample; 651 usable after lags |
| Chapter 7 | 1,855 out-of-sample days | after a 250-day initial training window |

**Gate 3's coverage was closed deliberately.** The threat/act split reads GDELT's
`Themes` field, which scans at roughly four times the cost of the `Locations`
field the other tests use — 0.88 TB against 0.24 TB across the full archive — so
it was first collected only for the six episode windows, 1,605 days. That left
the anticipation test running on about 40% of the corpus while everything else
used all of it, which is not a defensible asymmetry in a thesis whose argument
rests on the *absence* of an effect. The remaining 2,422 days were ingested at a
further 706 GB, and the test re-run on the full 4,027. The verdict did not change
— it fails under both timing conventions either way — but the pooled cell now
rests on **2,754 daily observations rather than 1,097**, which is what makes the
null worth stating. Gates 4 and 5 drew their own continuous ingests — 944 days of
gas-crisis coverage and 954 days for the escalation test — each collected
*after* its pre-registration was written. Between those and subsequent fill
collection, cumulative coverage ultimately reached the 4,027 days reported above.
A test's sample is the sample it ran on, and the gate results report theirs.

## 3.3 The equity spine

The equity half is built from Yahoo's chart endpoint, with **no vendor
credential and no cost**. This is worth stating because an earlier assessment in
this project concluded the opposite — that the equity spine could not be built
without a keyed vendor. That conclusion was drawn from a cloud session, whose
shared egress IP Yahoo rate-limits; from a residential connection the same
endpoint serves full history for every ticker the thesis needs. The distinction
is between a network condition and a data availability constraint, and the two
were confused.

**Nineteen tickers**, in four groups:

| group | tickers |
|---|---|
| US defence | LMT, RTX, NOC, GD, LHX, HII, BA |
| European defence | RHM.DE, HO.PA, BA.L, LDO.MI, SAAB-B.ST, AM.PA |
| sector ETFs | ITA, XAR, PPA |
| benchmarks | ^GSPC (S&P 500), ^STOXX (STOXX Europe 600), ^VIX |

Names are included only if their listing history reaches 2015. Hensoldt (listed
2020) and Renk (listed 2024) are excluded on that rule even though both are
obvious European defence exposures, because a basket whose composition changes
mid-sample would show the change as a return.

The spine runs **18 February 2015 to 29 June 2026, 2,837 trading days**. Returns
use the dividend- and split-adjusted close; the high and low used for
range-based volatility are raw, since mixing adjusted and unadjusted prices
misstates the daily range.

Including `^STOXX` matters more than its place in a ticker list suggests. The
Bloomberg-only preliminary work had no European benchmark and used the S&P 500
as the market control for both indices. Chapter 8 shows what that substitution
cost: supplying the correct regional control is what retracted an intermediate
result of this thesis.

## 3.4 Bloomberg as referee, and a validation that failed

Two proprietary series survived from the earlier phases of the project:
**WAERLST** (global aerospace and defence, USD) and **BSHIELDT** (European
defence, EUR), covering **January 2020 to June 2026, 1,698 days**.

They are not the main series, and the reason is a construction decision taken in
advance. Splicing free data for 2015–2019 onto Bloomberg for 2020–2026 would
place a change of measurement roughly two months before the one event the thesis
is built around, so any break estimated at February 2022 would be partly an
artefact of the join. The design therefore uses **one consistent free-data series
across the whole window**, with Bloomberg as an independent referee on the
2020–2026 overlap. Where the two agree that is a robustness result; where they
disagree, that needs to be known before the defence rather than after.

Whether the free baskets are close enough to serve was settled by a test with
criteria fixed before it was run: correlation of daily returns ≥ 0.95,
correlation of 20-day realised volatility ≥ 0.90, regression beta in 0.85–1.15,
regression R² ≥ 0.90, and tracking error ≤ 0.50 percentage points per day.
Computed on the 1,619 overlapping trading days:

| series | return ρ | vol ρ | beta | R² | tracking error | passed |
|---|---|---|---|---|---|---|
| US basket vs WAERLST | 0.890 | 0.964 | 0.888 | 0.793 | 0.725 | no |
| European basket vs BSHIELDT | 0.904 | 0.875 | 0.926 | 0.817 | 0.794 | no |
| ITA vs WAERLST | 0.955 | 0.987 | 1.032 | 0.911 | 0.501 | no |
| XAR vs WAERLST | 0.895 | 0.961 | 1.033 | 0.801 | 0.799 | no |
| PPA vs WAERLST | 0.934 | 0.976 | 0.893 | 0.873 | 0.554 | no |

**All five candidates fail.** ITA is the near miss: it clears four of the five
criteria and misses tracking error by **0.0013** percentage points per day. The
protocol's overriding criterion is whether the substitution changes the verdict
of the headline regression rather than whether every statistic clears its
threshold, and on that criterion ITA is usable as the global aerospace and
defence proxy. It is retained on that basis, with the marginal statistic stated
rather than rounded away.

**The European basket is genuinely weak at ρ = 0.904**, and there is no
long-history European defence ETF to substitute for it. This is a limitation that
travels with every European result before 2020, not a footnote: for that
sub-sample the European series is a hand-built basket whose daily variation
diverges measurably from the index a practitioner would use. Where a European
result is reported before 2020, it should be read with that in mind.

## 3.5 Geopolitical risk and macro controls

The **Caldara–Iacoviello daily geopolitical risk index** is used as the published
external benchmark, in its headline form and in its realised-acts and threats
decomposition. It is daily since 1985 and therefore covers the full sample with
no back-extension. It plays two roles: an external validation target for the
perception indices in Chapter 4, and the basis for the episode detector of
Chapter 5, which identifies anticipation windows without ever consulting an
asset price.

Five daily controls come from FRED, none requiring an API key: `VIXCLS`,
`DCOILBRENTEU` (Brent), `DEXUSEU` (USD/EUR), `DGS10` (10-year Treasury) and
`DTWEXBGS` (broad dollar). The macro spine is assembled on a calendar-day basis —
**4,151 days, 18 February 2015 to 30 June 2026** — with 100% coverage on the
geopolitical risk series and all five controls. Calendar days rather than trading
days, because the news indices are defined every day and the convention that
Friday's news predicts Monday's return needs weekend rows to exist.

## 3.6 The war-regime calendar

Every date carries one of four regime labels. The previous version collapsed the
conflict into a single `days_since_invasion` counter, which on an attrition-only
sample is nearly indistinguishable from any war indicator; on an eleven-year
sample the conflict has phases, and the phase is what carries the information.

| regime | window | trading days |
|---|---|---|
| pre-war | 2015-02-18 → 2021-10-31 | 1,678 |
| build-up | 2021-11-01 → 2022-02-23 | 79 |
| invasion | 2022-02-24 → 2022-09-28 | 149 |
| attrition | 2022-09-29 → 2026-06-29 | 931 |

The attrition regime is the previous version's entire sample. The build-up is
only 79 trading days but is analytically the most valuable window in the sample,
for reasons Chapter 5 sets out.

## 3.7 What no longer exists

Two datasets that the research design assumed were available are gone, and the
loss is not recoverable within this project.

The **constituent-level price files** behind WAERLST and BSHIELDT — 118 and 36
firms — and the **SIPRI arms-revenue shares** used to construct firm-level war
exposure did not survive the project's data attrition. The Bloomberg index levels
survived; the panels underneath them did not.

The consequence is specific. The exposure-gradient question — whether firms with
larger arms-revenue shares respond more strongly to geopolitical risk, and
whether that gradient differs across the February-2022 break — is **untestable
here**. There is no cross-section left to estimate it on, so this thesis makes no
firm-level claim at all and reports no exposure interaction. The project's own
planning documents still list both sources as available; that listing is stale,
and this is the correction.

Everything reported in Chapters 5 through 8 is therefore an index-level or
ecosystem-level result on a single time-series sample.

## 3.8 What this sample can rule out

The sample's size is what turns the null results of Chapter 7 into findings
rather than silences. Simulated on the out-of-sample evaluation window, a true
out-of-sample R² of **0.5% is detectable at 82% power and 0.2% at 43%**, against
a best observed value of **0.11%**. Predictability across most of the range this
literature reports is ruled out by this sample; only the region below it is not, and
Chapter 7 states the bound rather than claiming more than it can.
