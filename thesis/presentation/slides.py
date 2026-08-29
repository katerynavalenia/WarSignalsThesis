"""The content of the defence deck, in one place.

``make_pptx.py`` and ``make_beamer.py`` both import ``DECK`` from here, so the
.pptx and the PDF cannot drift apart: a bullet edited here changes both.

Authoring convention, obeyed by every string in this file:

* Prose is **plain text**. Characters LaTeX treats as special --- ``%``, ``&``,
  ``#``, ``_`` --- are written literally; ``make_beamer.py`` escapes them.
  Never write a LaTeX command in prose.
* ``**bold**`` is the main inline markup: a bold run in PowerPoint,
  ``\\textbf{}`` in LaTeX. ``*italic*`` likewise, for emphasis in a sentence.
* ``$...$`` is LaTeX maths, passed to LaTeX verbatim and rendered into unicode
  for PowerPoint by ``mathtext.to_unicode``. Every superscript, Greek letter
  and times sign goes through it, so neither renderer has to guess at a glyph.
* ``---`` is an em dash and ``--`` an en dash, as in LaTeX.
* A table row whose trailing cells are all empty is rendered as an italic
  group heading spanning the table.

Every number here is transcribed from ``thesis/final/thesis.tex``, which was
itself checked against ``outputs/tables/`` on 2026-08-26; ``check_numbers.py``
verifies that mechanically. Before changing one, read
``docs/findings_status.md``: six claims in this project were retracted, and
none of them may appear on a slide as a live result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Sections, in the order the talk runs. The labels appear in the slide header;
# the deck has no divider slides, because at a ten-to-fifteen minute length
# four of them would cost content for no orientation.
# ---------------------------------------------------------------------------

WHY = "Why this topic"
RQ = "Research question and contribution"
DATA = "Data sources and sample"
IDENT = "Identification strategy and model"
RESULTS = "Results"
FINDINGS = "Findings"
ROBUST = "Robustness"
CONCLUSION = "Conclusions"
BACKUP = "Backup"

SECTIONS = [WHY, RQ, DATA, IDENT, RESULTS, FINDINGS, ROBUST, CONCLUSION]


@dataclass
class Bullet:
    """One line of body text. ``level`` 0 is a top-level point, 1 an indent."""

    text: str
    level: int = 0


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    aligns: str = ""            # one of l/c/r per column; defaults to l then c
    note: str = ""
    rules_after: list[int] = field(default_factory=list)  # 0-based row indices

    def alignment(self) -> str:
        if self.aligns:
            return self.aligns
        return "l" + "c" * (len(self.headers) - 1)


@dataclass
class Slide:
    section: str
    title: str
    bullets: list[Bullet] = field(default_factory=list)
    figure: str = ""
    caption: str = ""
    table: Table | None = None
    notes: str = ""
    kind: str = "content"       # content | title
    subtitle: str = ""
    author: str = ""
    date: str = ""


def b(text: str, level: int = 0) -> Bullet:
    return Bullet(text, level)


# ===========================================================================
# Title
# ===========================================================================

TITLE_SLIDE = Slide(
    section="",
    kind="title",
    title="Whose Perception of Geopolitical Risk Is Priced in Defence Equities?",
    subtitle="Evidence from the Russia--Ukraine War",
    author="Khrystyna Kateryna Valenia",
    date="Master's thesis defence, August 2026",
    notes=(
        "The thesis asks a measurement question this literature has not asked: "
        "geopolitical-risk indices are built from English-language newspapers, "
        "so whose perception is actually being priced? The answer is a null on "
        "local-language coverage, and the talk is organised so that the "
        "robustness section -- which is what makes a null informative -- gets "
        "the weight it needs."
    ),
)


# ===========================================================================
# Roadmap
# ===========================================================================

ROADMAP = Slide(
    section="",
    title="Roadmap",
    bullets=[
        b("**Why this topic** --- the repricing to be explained, and what the literature leaves open"),
        b("**Research question and contribution**"),
        b("**Data sources and sample** --- why the obvious corpus will not do"),
        b("**Identification strategy and model** --- a conditional joint test with a positive control"),
        b("**Results** --- four tests, two asset classes, one non-market outcome, and out of sample"),
        b("**Findings** --- what a null of this kind does and does not license"),
        b("**Robustness** --- why this null is a finding rather than an absence"),
        b("**Conclusions**"),
    ],
    notes=(
        "Twenty seconds. Flag that Results and Findings are deliberately "
        "separate: first what the tests returned, then what they mean."
    ),
)


# ===========================================================================
# 1. Why this topic
# ===========================================================================

WHY_TOPIC = Slide(
    section=WHY,
    title="The repricing to be explained",
    bullets=[
        b("Europe **+21.6%** in the five weeks from 24 February 2022; **+7.0%** globally, **+9.1%** in the US."),
        b("Then a second and larger step: Europe **+63.7%** in the first half of 2025, on rearmament budgets."),
        b("**What information drove that repricing?**"),
    ],
    figure="fig1_defense_indices.png",
    caption="Defence-equity index levels, 1 January 2020 = 100. Dashed line: 24 February 2022.",
    notes=(
        "The sharpest repricing of defence equities in decades, in the most "
        "intensively covered armed conflict in modern media history. Point at "
        "the orange line: two steps, not one -- and the larger of the two is a "
        "fiscal announcement rather than battlefield news, which is already a "
        "reason to test war news against a market control rather than in "
        "isolation."
    ),
)

LITERATURE = Slide(
    section=WHY,
    title="What the literature establishes --- and the gap",
    bullets=[
        b("**Risk measured from newspaper text.** Baker et al. (2016) and Caldara and Iacoviello (2022) established normalised newspaper counts as a workable proxy. Both are built from a fixed panel of English-language, mostly American and British outlets."),
        b("**Media content moves prices.** Tetlock (2007) at short horizons; Manela and Moreira (2017) at long ones."),
        b("**Defence equities and conflict are more equivocal than the summaries suggest.** Event studies find sharp responses at onsets --- Covachev and Fazakas (2024) up to 12%, Klomp (2025) 10--15%. But continuously measured geopolitical risk predicts defence *volatility*, not returns: Apergis et al. (2018), Zhang et al. (2023)."),
        b("**The closest paper.** Bondarenko et al. (2024): for the Russian domestic economy, local Russian-language risk measures carry information that English-language measures do not."),
        b("**The gap.** No study separates news by the nationality of the outlet that published it. So when a defence-equity price is said to respond to geopolitical risk, it is responding to a quantity built from **one editorial vantage point** --- and that vantage point is an untested modelling assumption."),
    ],
    notes=(
        "The last bullet is the hinge of the whole talk. Say it slowly. "
        "Bondarenko is the paper this thesis mirrors: they run the test on the "
        "Russian economy, this runs it on the counterparty's assets."
    ),
)


# ===========================================================================
# 2. Research question and contribution
# ===========================================================================

RESEARCH_QUESTION = Slide(
    section=RQ,
    title="Research question and contribution",
    bullets=[
        b("**Whose perception of geopolitical risk is priced in defence equities?**"),
        b("Two candidate answers:"),
        b("*Either* the information originates where the war is fought --- local media are closer, cover it earlier and far more heavily --- and reaches Western prices with a delay.", 1),
        b("*Or* local coverage adds nothing once the Western signal is already in the regression.", 1),
        b("Only the second is directly testable, because it is a statement about **incremental** information. Establishing the positive claim that Western coverage is itself priced would need a different design, and is not claimed here."),
        b("**Contribution.** (i) The mirror of Bondarenko et al. (2024), run on the counterparty's assets. (ii) The editorial vantage point made the object of study rather than an assumption. (iii) A methodological point: at corpus level, this class of measurement error is invisible in the output. (iv) A refinement of the defence-equity literature --- the response is specific to the Western reporting layer."),
    ],
    notes=(
        "Be precise about the asymmetry between the two candidate answers. The "
        "design identifies an incremental contribution and nothing more; every "
        "version of the claim in the thesis is careful about this, and the "
        "committee will test whether the talk is too."
    ),
)


# ===========================================================================
# 3. Data sources and sample
# ===========================================================================

MEASUREMENT = Slide(
    section=DATA,
    title="The measurement problem that dictates the data",
    bullets=[
        b("Comparing national media ecosystems requires a corpus that actually contains them. The stream most readily available for this --- GDELT's Global Knowledge Graph 1.0 --- does not."),
        b("A representative daily file holds **60,690 records**. Of these, **7** carry a .ru domain and **21** a .ua domain."),
        b("Nationality in that stream can be assigned only from the countries an article *mentions*, which for **88.6%** of articles is not the country that published it."),
        b("A series built that way and labelled Ukrainian sentiment therefore measures the tone of **English-language writing about Ukraine** --- one editorial population sorted by topic and relabelled as three perspectives. Any comparison between them compares two topic proxies, not two vantage points."),
        b("**The fix:** GDELT's translingual archive --- **65 source languages**, machine-translated through a single annotation pipeline, with each article identified by **the outlet that published it**."),
    ],
    notes=(
        "This slide justifies the whole data effort, and it is also "
        "contribution (iii): the error is invisible in the output. The series "
        "are well behaved, they correlate with events, they differ from one "
        "another -- and they are still measuring the wrong thing."
    ),
)

ECOSYSTEMS = Slide(
    section=DATA,
    title="Five ecosystems, classified by publisher",
    bullets=[
        b("**UA, RU_STATE, RU_INDEP, WEST, EN_GLOBAL.** An article in a British newspaper about Russian troop movements is Western, not Russian."),
        b("Four tiers in priority order: a hand-curated register, then national domain suffix, then source language conditional on country, then a residual category."),
        b("**Country beats language at every tier.** Ukrainian outlets publish heavily in Russian --- 24tv.ua carries 2,595 Ukrainian-language and 1,865 Russian-language articles. A language-first rule would file those as Russian and manufacture agreement between two ecosystems the design must keep apart."),
        b("**One rule, pointing both ways.** State-funded external broadcasters classify to the funding state, which puts Deutsche Welle and RFE/RL in the Western block; exile newsrooms classify to their country of origin, which keeps Meduza in the Russian independent one."),
        b("**Validated externally, not asserted.** Each registered domain is resolved against Wikidata: of 84 outlets, 66 resolve and **63 agree --- precision 0.955**. All three disagreements are exile newsrooms, the one case where origin and operation genuinely differ."),
    ],
    notes=(
        "If asked what the audit does not do: it validates that a registered "
        "domain belongs to the country assigned to it. It does not validate "
        "GDELT's attribution of a given article to a domain -- that would need "
        "a reader with Russian and Ukrainian."
    ),
)

VARIABLES = Slide(
    section=DATA,
    title="Variables, targets and sample",
    bullets=[
        b("**Two perception indices per ecosystem per day.** *Ukraine/Russia coverage share* --- articles whose GDELT location field names a place in Ukraine or Russia, over the ecosystem's **entire** daily output. *Coverage tone* --- mean GDELT tone of those same articles."),
        b("**A third, theme-based split** following Caldara and Iacoviello (2022): anticipatory coverage of threats and build-ups against realised coverage of acts and attacks. Conflict-specific by construction."),
        b("**Shares, never raw counts.** GDELT source coverage drifts by a factor of two and a half over eleven years; a count series would show that drift as a trend in every ecosystem at once."),
        b("**Changes, never levels.** In levels every series carries a common war-regime trend that the financial controls already capture."),
        b("**Five targets:** Bloomberg WAERLST (global) and BSHIELDT (Europe) from 2020; the ITA ETF back to 2015; and two hand-built equal-weighted baskets."),
        b("**Sample: 4,027 days, 18 February 2015 to 20 May 2026, 98% of calendar days**; 3,073 carry all five ecosystem series. Supplementary: Ukrainian Air Force records --- 3,812 attack records, 102,396 weapons launched, **74.3%** intercepted."),
    ],
    notes=(
        "Flag the honest limitation now rather than being asked. For a Western "
        "outlet, naming a Ukrainian place implies conflict coverage; for a "
        "Ukrainian outlet it implies very little, because domestic politics, "
        "business and sport all name Ukrainian places. The local series sit "
        "near a ceiling. It returns on the conclusions slide, bounded two ways."
    ),
)


# ===========================================================================
# 4. Identification strategy and model
# ===========================================================================

IDENTIFICATION = Slide(
    section=IDENT,
    title="Identification strategy and model",
    bullets=[
        b("$r_{i,t} = \\alpha + \\beta_{West} X^{West}_{t} + \\beta_{Local} X^{Local}_{t} + \\gamma Z_{t} + \\varepsilon_{i,t}$"),
        b("The object of interest is a **joint $F$-test on $\\beta_{Local}$, with the Western block already in the regression.** That conditioning is what separates local media adding something from local and Western media correlating with returns for the same reason."),
        b("**The positive control is the identical test on $\\beta_{West}$, in the same cells.** If the design detects neither block, a null on the local block means nothing. This is what makes the result a finding."),
        b("**The market control must be regional.** European defence returns are controlled with the STOXX 600, not the S&P 500. Over the build-up the two markets correlate only 0.409, so a US control leaves ordinary European variation in the residual --- and that residual correlates 0.26 with the threat measure being tested."),
        b("Two controls only, plus HAC(5) standard errors throughout. The grid crosses two frequencies, six episode windows plus the full sample, and five targets: 70 cells, of which **31** clear a minimum-observation rule."),
        b("**31 tests at 5% would produce about 1.5 false rejections by chance**, so Benjamini--Hochberg correction is applied across all 31 at a 5% false discovery rate. Gates 3, 4 and 5 are **pre-registered**; **Gate 2 is not**, and is reported as the exploratory test it is."),
    ],
    notes=(
        "Do not blur the pre-registration line: Gate 2 was never "
        "pre-registered and the thesis says so explicitly. For Gates 4 and 5 "
        "the data were collected only after the pre-registration was "
        "committed, so the ordering is verifiable from commit timestamps "
        "rather than asserted."
    ),
)


# ===========================================================================
# 5. Results
# ===========================================================================

TWO_WORLDS = Slide(
    section=RESULTS,
    title="Descriptive: two media worlds, an order of magnitude apart",
    bullets=[
        b("Local outlets: **71--85%** of output names a Ukrainian or Russian place. Western: **7.2%**. Native-English: **5.4%**."),
        b("At the invasion Western attention moves **19.0% to 40.9%** in a day --- Ukrainian only 90.3% to 95.8%."),
        b("**The local ecosystems had almost no headroom left to react.**"),
    ],
    figure="fig1_attention_full_sample.png",
    caption="Ukraine/Russia coverage share by ecosystem, 30-day moving averages, 2015--2026.",
    notes=(
        "The order-of-magnitude gap is sustained across eleven years, and the "
        "gap between the upper three lines and the lower two is the whole "
        "point of the panel. Native-English moves 11.8% to 23.8% on the same "
        "two days, Russian state 84.6% to 91.2%. This is the mechanical reason "
        "a Western investor watching coverage volume would have seen a signal "
        "in Western outlets and very little in local ones: a series already at "
        "four-fifths of output cannot rise much when the event arrives."
    ),
)

TONE_ASYMMETRY = Slide(
    section=RESULTS,
    title="Descriptive: the tone asymmetry at the invasion",
    bullets=[
        b("Tone shift at the invasion: Ukrainian **$-1.66$**, native-English $-0.64$, Western $-0.36$ --- **Russian state $+0.02$**."),
        b("**Not a composition artefact:** on a fixed panel of the 24 state outlets present on both sides, the shift is **$-0.05$**."),
        b("**The signal that moved most sharply at the defining event of the sample is not the one prices track.**"),
    ],
    figure="fig2_tone_full_sample.png",
    caption="Mean coverage tone by ecosystem, 30-day moving averages, 2015--2026.",
    notes=(
        "Russian state media's tone did not change when Russia invaded "
        "Ukraine, and Russian independent moved +0.09. Several state outlets "
        "became more positive -- Gazeta.ru +0.48, Ren.tv +0.43 -- which is "
        "what one would expect from outlets covering the launch of an "
        "operation their government had announced as a success. A "
        "supremum-Wald test for a break at an unknown date puts Ukrainian "
        "tone's largest break on 24 February 2022 and Russian state tone's 393 "
        "days later. This is the largest and most robust descriptive fact in "
        "the corpus. Note it is the state-versus-Ukraine contrast; the "
        "state-versus-independent comparison does not survive and is not "
        "claimed."
    ),
)

GATES_23 = Slide(
    section=RESULTS,
    title="Gates 2 and 3: local perception and defence-equity returns",
    table=Table(
        headers=["Block and news timing", "Cells", "BH surv.", "Min. $p$", "Verdict"],
        rows=[
            ["Gate 2 --- coverage volume and tone (exploratory)", "", "", "", ""],
            ["Local, lagged one day (primary)", "31", "1", "$9.0\\times10^{-4}$", "not robust"],
            ["Local, same-day", "31", "7", "$2.2\\times10^{-6}$", "not tradeable"],
            ["Western, lagged one day (control)", "31", "0", "$2.7\\times10^{-3}$", "not detected"],
            ["Gate 3 --- anticipated/realised split (pre-registered)", "", "", "", ""],
            ["Local, lagged one day (primary arm)", "31", "2", "$5.5\\times10^{-6}$", "**FAIL**"],
            ["Western, lagged one day (control)", "31", "2", "$1.6\\times10^{-4}$", "**detected**"],
        ],
        aligns="lcccc",
        rules_after=[3],
        note=(
            "Joint $F$-tests on one block, with the other block and the controls already in the "
            "regression. Benjamini--Hochberg at 5% FDR across all 31 cells of an arm."
        ),
    ),
    bullets=[
        b("**The timing contrast is the sensitivity evidence.** Local coverage is detected in **7 of 31** cells when credited to its publication day, and in **1 of 31** when lagged one trading day so that all of it precedes the open --- and that one cell is the 2017--19 window on ITA at weekly frequency, years before the full-scale invasion."),
        b("**Gate 3 fails both pre-registered arms.** The build-up window produces no survivor (smallest $p$ 0.018), and the two that do survive share a window where the rule required two. Both are weekly cells fitting 13 parameters to 58 observations, while the grid's two deepest cells --- 2,754 observations --- return $p = 0.08$ and 0.36."),
        b("**The Western block is detected in the same 31 cells, under the same correction.** That asymmetry is what the test was built to isolate."),
    ],
    notes=(
        "If asked what the seven-to-one collapse proves: it is consistent with "
        "same-day news being impounded within the trading day, with a "
        "mechanical artefact of matching a return to coverage partly published "
        "after it, and with information that decays inside 24 hours. Daily "
        "aggregates cannot separate those. What it does establish is narrower "
        "and enough -- the design detects the local block readily under the "
        "permissive alignment, so the null under the conservative one is not a "
        "failure to measure."
    ),
)

GATES_45 = Slide(
    section=RESULTS,
    title="Gates 4 and 5: gas and escalation",
    table=Table(
        headers=["Gate and window", "$n$", "$p$ (local)", "$p$ (Western)"],
        rows=[
            ["Gate 4 --- Dutch TTF natural gas returns", "", "", ""],
            ["(a) Build-up and invasion, daily", "222", "0.399", "**0.00004**"],
            ["(b) Shutdown and aftermath, daily", "231", "0.533", "0.193"],
            ["(c) Full crisis, daily", "563", "0.250", "0.066"],
            ["(c) Full crisis, weekly", "133", "0.907", "0.052"],
            ["Gate 5 --- realised escalation, held-out sample", "", "", ""],
            ["Horizon $h = 1$ day", "637", "0.212", "0.171"],
            ["Horizon $h = 5$ days", "629", "0.227", "**0.033**"],
        ],
        aligns="lccc",
        rules_after=[4],
        note="Both gates were pre-registered before their data were ingested. All four Gate 4 cells estimated are reported.",
    ),
    bullets=[
        b("These answer the fair objection that **defence equities are a weak testbed** --- the link from a Russian newspaper to a US contractor's share price runs entirely through Western investors."),
        b("**Gas has a direct physical channel:** Russia supplied roughly 40% of EU gas, and TTF went from about 20 euro to over 300. Yet **all four pre-registered conditions fail** --- no surviving cell; the Brent placebo breached at $p = 0.0014$; 0.399 becoming 0.840 without the ten largest TTF moves; and the ordering inverted. **Western detected at $p = 4\\times10^{-5}$.**"),
        b("**Escalation removes prices entirely.** On 637 held-out days local media do not lead realised conflict. The weakest of the four gates: its own Western control is significant at five days, not at one."),
    ],
    notes=(
        "The Brent placebo matters because Brent is an asset the "
        "supply-signalling mechanism does not predict, so local perception "
        "being jointly significant for it is a breach. The inverted ordering "
        "is Russian independent rather than Russian state media leading the "
        "local block -- the wrong way round for a channel supposed to run "
        "through state signalling of supply intent. Gate 4 also shows how a "
        "result dissolves under replication alone: estimated on 81 days it "
        "returned p = 0.0028, and the pre-registered confirmatory estimate on "
        "222 days of the same calendar period, with nothing altered but the "
        "quantity of data, returned 0.399."
    ),
)

OUT_OF_SAMPLE = Slide(
    section=RESULTS,
    title="Out of sample --- and what a null can bear",
    table=Table(
        headers=[
            "True $R^{2}_{OS}$ implanted",
            "Long sample (1,855 days, 3 targets)",
            "Bloomberg (686 days, 2 targets)",
        ],
        rows=[
            ["0.0% (nominal size)", "0.02", "0.02"],
            ["0.2%", "0.40", "0.21"],
            ["**0.5%**", "**0.81**", "**0.44**"],
            ["1.0%", "0.98", "0.76"],
            ["2.0%", "1.00", "0.97"],
        ],
        aligns="lcc",
        note=(
            "Simulated power: rejection rate at the 5% level, 1,000 paths per cell, so each entry "
            "carries a standard error of at most 1.6 percentage points."
        ),
    ),
    bullets=[
        b("50 specifications --- five targets by ten predictors --- in an expanding window, one day ahead. Every comparison is **nested**, so it is arbitrated by **Clark--West, not Diebold--Mariano**: under nesting DM has no standard normal limiting distribution and is biased against the larger model even when its extra predictor carries real information."),
        b("**Zero rejections, against 2.5 expected by chance.** Best $R^{2}_{OS}$ observed **+0.10%**; smallest $p$-value 0.067, so not one specification reaches even nominal significance."),
        b("**The power simulation is what makes that informative --- and it must be read as two numbers, never one.** On the three long-sample targets an effect of 0.5% is detected in **81%** of paths, and one of 1.0% in **98%**. On the two Bloomberg targets the same effects give **44%** and **76%**, so there a meaningful effect would be missed more often than not, and the null is weak evidence rather than a bound."),
        b("**Power is not exclusion.** 81% means one sample in five misses a real effect."),
    ],
    notes=(
        "The claim is bounded in both directions and must be stated that way: "
        "an effect large enough to matter economically would very probably "
        "have been seen on the long-sample targets, and an effect that escaped "
        "this design lies at or below the bottom of the range the "
        "predictability literature treats as economically meaningful. The 0.5 "
        "to 1.0% band is Welch and Goyal (2008) and Campbell and Thompson "
        "(2008)."
    ),
)


# ===========================================================================
# 6. Findings
# ===========================================================================

WHAT_IT_MEANS = Slide(
    section=FINDINGS,
    title="What this means",
    bullets=[
        b("**Local-language perception adds nothing to defence-equity returns conditional on Western coverage** --- in coverage volume, in tone, in the anticipated/realised structure, across two asset classes, against one non-market outcome, and out of sample. The null is consistent across all four tests."),
        b("**This is a finding rather than an absence, because the design demonstrably detects media effects.** The Western block survives correction in the pre-registered anticipation test and is detected at $p = 4\\times10^{-5}$ in gas; the local block itself is detected in 7 of 31 cells before the tradeable lag is imposed. The informative feature is the **co-occurrence** --- a null on the local block in precisely the cells where an effect is found on the Western one."),
        b("**The descriptive asymmetry points the same way.** Russian state tone did not move at the invasion and local attention was already at saturation, while Western attention doubled in a day. If the marginal buyers of Western defence equities form their views from Western coverage, they responded to the one series that registered the event."),
        b("**The mirror of Bondarenko et al. (2024) comes back reversed --- but the symmetric positive claim is not made.** This design identifies the local block's incremental contribution, not the Western block's own effect. What the two studies jointly support is narrower and more useful: **the informative ecosystem is the one inhabited by the agents whose decisions are being measured.**"),
    ],
    notes=(
        "The fourth bullet is where a committee will push. Hold the line: "
        "establishing that Western coverage is priced would require it to be "
        "detected consistently rather than in some tests and not others, and "
        "the evidence falls short of that. Neither result licenses a general "
        "claim that local media always or never matter."
    ),
)


# ===========================================================================
# 7. Robustness
# ===========================================================================

ROBUSTNESS_BATTERY = Slide(
    section=ROBUST,
    title="Robustness: the tests that could have overturned this",
    bullets=[
        b("**The classification rule.** Five rules run through the full grid --- baseline, register-only, no language tier, language-first, and aggregators retained. The verdict is unchanged under all five: one or two survivors of 31. Language-first is the informative failure: it **cannot represent a Russian independent block at all**, because the language tier claims those articles before ownership is consulted."),
        b("**Aggregation.** An index-level null could mask cross-sectional variation. A firm-level panel of **31 defence names and 85,065 firm-days**, with exposure from published SIPRI arms revenue, produces no exposure gradient in any war window --- nominal significance appears only in the years *before* the full-scale invasion, and **0 of 10 cells survive correction**."),
        b("**The physical war itself**, in case the news measures are simply a poor proxy for it. A forecasting race over **144 specifications** and five information sets: 16 achieve a positive $R^{2}_{OS}$ and **none survives correction**. Realised attack intensity is no more informative about subsequent defence returns than perceived intensity."),
        b("**Volatility**, where a positive result was most plausible, since volatility is persistent where returns are not. Forty-eight augmented HAR-RV-X specifications: **none improves significantly**, eight are significantly worse, and all six correction survivors are deteriorations. Reported with its limit --- on a squared-daily-return proxy the HAR family is roughly twice as inaccurate as GARCH, so the test has limited power."),
        b("Both forecasting exercises are **exploratory, not pre-registered**, and are labelled that way."),
    ],
    notes=(
        "Say plainly that the last two are the weakest evidence in the thesis "
        "and that the volatility one is bounded by its own measure. Claiming "
        "more for them than they support is exactly the failure the next slide "
        "is about."
    ),
)

SIX_DISSOLVED = Slide(
    section=ROBUST,
    title="Six results that dissolved --- and why that matters",
    table=Table(
        headers=["The result, when it was significant", "What eliminated it"],
        rows=[
            ["Defence volatility responds to threat", "The regional market control (S&P 500 to STOXX 600)"],
            ["Threat moves returns in the build-up, $p = 0.0001$", "The same control: $p$ becomes 0.84"],
            ["Gate 3 clears its pre-registered rule, 7 survivors", "Adding the held-out window: 7 becomes 2, verdict FAIL"],
            ["Local perception priced in gas, $p = 0.0028$ on 81 days", "Replication on 222 days of the same period: $p$ becomes 0.399"],
            ["Local media anticipate escalation, both halves", "The pre-registered held-out sample: $p$ becomes 0.21"],
            ["A state-versus-independent censorship wedge", "Correcting the outlet register: $p = 0.561$"],
        ],
        aligns="ll",
        note=(
            "Each correction to the register moved the last one *further* from significance. "
            "None of the six is claimed as a result anywhere in the thesis."
        ),
    ),
    bullets=[
        b("Each was significant at conventional levels, each admitted a plausible economic mechanism, and each survived at least one robustness check before failing another. **The six failure modes are all different** --- two omitted variables, one truncated sample, one small sample, one in-sample split that did not generalise, one composition change."),
        b("**In every case the eliminating test is one that a study reporting the positive would have had no particular reason to run.** That is what bounds how much confidence a single significant specification warrants in this literature."),
        b("They are reported rather than suppressed because **in a literature whose regressors are constructed from text, the set of choices under which a result survives is part of the result** --- and a null established against this background is considerably more informative than one obtained without it."),
    ],
    notes=(
        "This is the methodological core, and the strongest answer to 'how do "
        "we know you did not simply fail to find something'. The honest "
        "framing: the project generated six plausible positives and killed all "
        "six with tests it chose to run on itself."
    ),
)


# ===========================================================================
# 8. Conclusions
# ===========================================================================

CONCLUSIONS = Slide(
    section=CONCLUSION,
    title="Conclusions",
    bullets=[
        b("**The answer.** Local coverage provides no robust incremental information about defence-equity returns beyond what Western coverage already carries. It is a null, not a reversal --- and it is not attributable to a design unable to detect media effects."),
        b("**The implication beyond this conflict.** Multilingual geopolitical-risk indicators are built on the premise that sources closer to an event carry information Anglophone coverage omits. Tested in close to the most favourable setting available --- eleven years, the most intensively covered conflict in modern media history, an asset class whose valuation rests on it, local media at near-saturation coverage --- **the premise does not hold at either horizon at which the information could have been traded.** It is not refuted in general. It cannot be assumed."),
        b("**Limitations, stated as bounds.** The coverage-share measure is close to a domestic-news filter for local outlets, so part of the null may be a ceiling --- bounded by Gate 3, which is theme-based and returns the same null, and by local daily changes being two to four times as variable as Western ones. The design is associational, not causal. GDELT tone is dictionary-based. And daily aggregates cannot resolve intraday timing; only timestamped data could settle what the Gate 2 contrast means."),
        b("**Extensions.** Other conflicts --- Israel--Hamas, the Taiwan Strait --- to separate a general property of defence-equity pricing from a feature of this war. Intraday prices, at which the anticipated-versus-realised distinction becomes observable. And assets whose marginal investors are **not** Western, which is the sharpest available test of the proposition that each market prices the information ecosystem its own participants inhabit."),
    ],
    notes=(
        "Close on the last extension: it is the proposition the whole thesis "
        "converges on, and the one a future paper could actually settle."
    ),
)


# ===========================================================================
# Backup
# ===========================================================================

B_SPECIFICATION = Slide(
    section=BACKUP,
    title="The main specification, estimated",
    table=Table(
        headers=["", "(1) Controls", "(2) +Western", "(3) +local, same-day", "(4) +local, lagged"],
        rows=[
            ["$\\Delta$ Ukrainian attention", "", "", "0.009", "$-0.011$"],
            ["$\\Delta$ Russian state attention", "", "", "$-0.001$", "$-0.001$"],
            ["$\\Delta$ Russian indep. attention", "", "", "$-0.125^{***}$", "0.010"],
            ["$\\Delta$ Ukrainian tone", "", "", "$-0.073^{*}$", "$-0.038$"],
            ["$\\Delta$ Russian state tone", "", "", "$0.127^{**}$", "$-0.055$"],
            ["$\\Delta$ Russian indep. tone", "", "", "0.033", "$-0.017$"],
            ["STOXX 600 return", "$0.925^{***}$", "$0.923^{***}$", "$0.927^{***}$", "$0.921^{***}$"],
            ["Log VIX (lagged)", "0.068", "0.066", "0.075", "0.066"],
            ["Observations", "921", "921", "921", "921"],
            ["$R^{2}$", "0.348", "0.351", "0.365", "0.354"],
            ["$p$, local block jointly zero", "---", "---", "**0.003**", "0.734"],
            ["$p$, Western block jointly zero", "---", "0.333", "0.688", "0.177"],
        ],
        aligns="lcccc",
        rules_after=[7],
        note=(
            "Dependent variable: daily percentage return on BSHIELDT, over the 921 days on which "
            "it trades and all five news series exist. News regressors are standardised first "
            "differences, so a coefficient is the return change per one-standard-deviation move. "
            "Western-block coefficients omitted for space; none is significant. Newey--West "
            "HAC(5). Stars: 1%, 5%, 10%."
        ),
    ),
    bullets=[
        b("Column (3) against column (4) is the whole story in one cell: the local block is jointly significant same-day at **$p = 0.003$**, and jointly indistinguishable from zero at **$p = 0.734$** once lagged by one trading day."),
    ],
    notes=(
        "Show this if anyone asks to see magnitudes rather than p-values. "
        "Regressors are standardised, so a coefficient reads as the "
        "percentage-point return change per one-standard-deviation move."
    ),
)

B_CLASSIFICATION = Slide(
    section=BACKUP,
    title="Does the classification rule drive the result?",
    bullets=[
        b("Five rules are run through the full 31-cell grid: the **baseline**; **register-only**, dropping the ccTLD and language tiers; **no language tier**; **language-first**; and one **retaining news aggregators**."),
        b("**The local-block verdict is unchanged under all five** --- one or two survivors of 31 under the primary alignment in every variant."),
        b("**Language-first is the informative failure.** Because the language tier claims Russian-language articles before ownership is consulted, it produces **no Russian independent block at all**. That is the concrete cost of getting the country-before-language rule wrong, and it is why the rule is stated as a rule rather than applied case by case."),
        b("Three outlets were in fact misfiled under the state-broadcaster rule before it was written down --- which is why that rule is stated in both directions."),
    ],
    notes="Source: outputs/tables/classifier_sensitivity.csv.",
)

B_MARKET_CONTROL = Slide(
    section=BACKUP,
    title="Why the regional market control is decisive",
    bullets=[
        b("Controlling European defence returns with the S&P 500 is superficially reasonable --- the two markets are highly correlated over long horizons."),
        b("**Over the build-up window their correlation is only 0.409.** A US control therefore leaves a substantial component of ordinary European market variation in the residual."),
        b("**That residual correlates 0.26 with the threat measure being tested**, so the omitted regional factor loads onto the variable of interest."),
        b("The consequence: a build-up threat effect significant at **$p = 0.0001$** under the S&P 500 control becomes **$p = 0.84$** under the STOXX 600. Two of the six dissolved results share this single cause."),
        b("Every regression in the thesis therefore uses the regional market return appropriate to its target: STOXX 600 for European targets, S&P 500 for global and US ones."),
    ],
    notes=(
        "If pressed on why this was not obvious from the start: it was not, "
        "and that is the point of reporting it. The correlation is high over "
        "long horizons and breaks down precisely in the window the test cares "
        "about."
    ),
)

B_CLARK_WEST = Slide(
    section=BACKUP,
    title="Why Clark--West and not Diebold--Mariano",
    bullets=[
        b("Forecast-accuracy comparisons in this literature are most often reported with the **Diebold--Mariano** statistic (1995). It is not valid here."),
        b("Each of the 50 specifications compares the historical mean **augmented with one perception predictor** against the historical mean alone. Setting that predictor's coefficient to zero recovers the benchmark exactly, so **the benchmark is nested within the model**."),
        b("Under nesting, DM has **no standard normal limiting distribution** and is **biased against the larger model** even when its additional predictor carries genuine information --- so a DM-based null here would be partly an artefact of the statistic."),
        b("**Clark and West (2007)** correct for the estimation noise that nesting introduces, giving a statistic that is valid in this setting and one-sided in the direction of improvement."),
        b("Diebold--Mariano with the Harvey et al. (1997) small-sample correction is retained for genuinely non-nested comparisons. In the code the two are separate functions, so the distinction cannot be flagged away."),
    ],
    notes="src/models/evaluation.py keeps them as separate functions deliberately.",
)

B_RETURN_RACE = Slide(
    section=BACKUP,
    title="Return forecasting race, by information set",
    table=Table(
        headers=["Set", "Contents", "Specs", "$R^{2}_{OS} > 0$", "Best $R^{2}_{OS}$", "BH surv."],
        rows=[
            ["F", "Financial controls only", "24", "1", "0.019", "0"],
            ["P", "F + physical attack variables", "24", "4", "0.073", "0"],
            ["N", "F + news variables", "24", "1", "0.033", "0"],
            ["PN", "F + physical + news", "24", "3", "0.060", "0"],
            ["PNG", "PN + pairwise ecosystem tone gaps", "24", "4", "0.059", "0"],
            ["", "Historical mean", "12", "0", "0.000", "---"],
            ["", "AR(1)", "12", "1", "0.009", "---"],
        ],
        aligns="llcccc",
        rules_after=[4],
        note=(
            "Expanding-window one-step-ahead forecasts on WAERLST, BSHIELDT and ITA, at horizons "
            "of one and five days, on the full sample and on the September 2022 to June 2026 "
            "attack subsample. Ridge and gradient boosting, 144 rows in total. Exploratory, not "
            "pre-registered."
        ),
    ),
    notes=(
        "Adding physical attack data to the financial controls raises the "
        "count of positive-R2 cells from one to four, and none of those four "
        "is significant. Baselines win 8 of 12 cells."
    ),
)

B_VOL_RACE = Slide(
    section=BACKUP,
    title="Volatility forecasting race, HAR-RV-X against HAR-RV",
    table=Table(
        headers=["Model", "Specs", "Mean QLIKE gain (%)", "Sig. better", "Sig. worse", "BH surv."],
        rows=[
            ["HAR-RV-X (N)", "12", "$-4.4$", "0", "1", "0"],
            ["HAR-RV-X (P)", "12", "$-65.0$", "0", "2", "2"],
            ["HAR-RV-X (PN)", "12", "$-62.6$", "0", "2", "2"],
            ["HAR-RV-X (PNG)", "12", "$-64.8$", "0", "3", "2"],
        ],
        aligns="lccccc",
        note=(
            "Mean QLIKE by model class, lower is better: GARCH 0.95, GJR-GARCH 0.96, EGARCH 0.98, "
            "**HAR-RV 1.93**. That last figure is the limitation, not an aside: realised variance "
            "here is the sum of squared daily returns, because intraday prices were not available, "
            "so the HAR family is roughly twice as inaccurate as the GARCH family it is normally "
            "competitive with."
        ),
    ),
    bullets=[
        b("Augmenting a volatility model with war variables **degrades** its accuracy on this measure rather than improving it: of 48 specifications none improves significantly, eight are significantly worse, and all six correction survivors are deteriorations."),
        b("What **cannot** be concluded is that conflict news carries no information about defence-equity volatility. A test built on squared daily returns has limited power to detect it."),
    ],
    notes=(
        "This is the weakest evidence in the thesis and should be presented "
        "that way. Apergis et al. (2018) find geopolitical risk predicting "
        "volatility in-sample, which is compatible with this: the question "
        "here is out-of-sample accuracy against models that already exploit "
        "the persistence of realised variance."
    ),
)

B_FIRM_LEVEL = Slide(
    section=BACKUP,
    title="Does the index-level null hide a cross-section?",
    bullets=[
        b("The objection is fair: an index-level null could mask cross-sectional variation, with heavily war-exposed firms responding where a diversified index does not."),
        b("**A firm-level panel of 31 defence names and 85,065 firm-days**, with exposure measured from published SIPRI arms-revenue data, tests it directly."),
        b("**No exposure gradient appears in any war window.** Nominal significance appears only in the years before the full-scale invasion, and in a full sample of which 59% falls in those years."),
        b("**0 of 10 cells survive Benjamini--Hochberg correction.** The index-level result is therefore not an artefact of aggregation."),
        b("Firm-level constituent and SIPRI exposure data could not be extended further, which is why the thesis carries no cross-sectional chapter and says so."),
    ],
    notes="Source: outputs/tables/exposure_gradient_bh.csv.",
)


# ===========================================================================
# The deck
# ===========================================================================

MAIN: list[Slide] = [
    TITLE_SLIDE,
    ROADMAP,
    WHY_TOPIC,
    LITERATURE,
    RESEARCH_QUESTION,
    MEASUREMENT,
    ECOSYSTEMS,
    VARIABLES,
    IDENTIFICATION,
    TWO_WORLDS,
    TONE_ASYMMETRY,
    GATES_23,
    GATES_45,
    OUT_OF_SAMPLE,
    WHAT_IT_MEANS,
    ROBUSTNESS_BATTERY,
    SIX_DISSOLVED,
    CONCLUSIONS,
]

BACKUP_SLIDES: list[Slide] = [
    B_SPECIFICATION,
    B_CLASSIFICATION,
    B_MARKET_CONTROL,
    B_CLARK_WEST,
    B_RETURN_RACE,
    B_VOL_RACE,
    B_FIRM_LEVEL,
]

DECK: list[Slide] = MAIN + BACKUP_SLIDES

# The cut to make if the slot turns out to be ten minutes rather than fifteen.
# Named here rather than in prose so the README and the deck cannot disagree.
TEN_MINUTE_CUT = [
    "Roadmap",
    "Variables, targets and sample",
    "Robustness: the tests that could have overturned this",
]
