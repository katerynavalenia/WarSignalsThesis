# Chapter 2 — Literature

This thesis sits at the intersection of two literatures that have grown quickly
and separately. One measures risk from text and asks what asset prices do with
it. The other asks whose text is being measured, and shows that the answer
changes the result. The first is large and the second is very small — small
enough that its central paper appeared in 2024 and has not yet been carried
across to asset prices at all. That is the gap this thesis occupies.

## 2.1 Risk measured from newspapers

The modern practice of reading a risk index off newspaper text begins with
Baker, Bloom and Davis (2016). Their economic policy uncertainty index counts
articles that jointly mention the economy, uncertainty and policy across a fixed
panel of newspapers, normalizes by each paper's total output, and produces a
monthly series that behaves as a reader of the period would expect it to. Two
features of that design have become conventions in everything that followed.
Coverage is measured as a *share* of the outlet's own output rather than as a
raw count, because the size of the underlying corpus drifts; and the index is
validated against human readers and known events rather than against another
statistical construct. Both conventions are adopted in Chapter 4, for reasons
that turn out to matter a great deal here.

Manela and Moreira (2017) push the same idea backwards in time. Their news
implied volatility index is fitted from front-page *Wall Street Journal* text to
option-implied volatility where the two overlap, then extrapolated over more
than a century where options data do not exist. The result is relevant to this
thesis for a substantive reason rather than a methodological one: the category
of news that contributes most to their measured uncertainty is war. Text-based
risk measurement and conflict have been entangled since the literature's
beginning.

Hassan, Hollander, van Lent and Tahoun (2019) move the unit of observation from
the newspaper to the firm, scoring quarterly earnings-call transcripts for
political risk. Their most useful result for present purposes is a negative one.
Most of the variation in firm-level political risk is idiosyncratic rather than
common: firms in the same industry and the same quarter differ sharply in how
exposed they are, and aggregating the measure discards most of its information.
That finding is a standing warning against assuming that an index built at the
national or global level maps cleanly onto any particular set of equities.

Caldara and Iacoviello (2022) supply the specific measure this thesis uses as an
external benchmark. Their geopolitical risk index counts articles in a fixed set
of newspapers matching search groups for war, military and terrorist events,
and — crucially for the research design of Chapter 6 — separates them into eight
categories, of which five concern *threats* (war threats, peace threats,
military build-ups, nuclear threats, terror threats) and three concern *acts*
(the beginning of war, its escalation, and terror attacks). The resulting
GPR_THREAT and GPR_ACT components allow anticipation to be separated from
realization within one consistently constructed corpus.

That decomposition is the conceptual engine of this thesis, and it is worth
being precise about why. If markets are forward-looking, the informative
component of a conflict indicator ought to be the anticipatory one; realized
events, once expected, should already sit in prices. A measure that pools
threats and acts cannot test this, and a design that proxies realization with an
external event count — attack tallies, casualty figures — cannot test it either,
because threats and acts would then be measured by different instruments
carrying different noise. Caldara and Iacoviello's split, and the analogous
split built from GDELT's theme taxonomy in Section 4.4, keep both sides on the
same measurement footing. Chapter 8 reports the one place in this sample where a
threat component is clearly priced: European equities as a whole load on threat
at +0.474 with p<0.0001 over the build-up and invasion — market-wide, not differentially in defence names, and not outside that window.

## 2.2 Whose newspapers

Every index described above is built from English-language sources, and in
almost every case from a small number of American or British outlets. This is
usually treated as a sampling detail. Bondarenko, Lewis, Rottner and Schüler
(2024, *Journal of International Economics* 152, 104005) show that it is an
identifying assumption. Theirs is the paper this thesis is built against: it
supplies the research question, the press-freedom control adopted in Section 4.3,
the local-versus-English contrast that Chapter 6's joint F-test operationalises,
and the standard against which the result of Chapter 9 is read. Everything else
in this chapter is apparatus.

Their argument is that geopolitical risk cannot be measured in a universal way,
because the risk that matters to an agent is the risk that agent perceives.
Taking Russia as a case study, they construct geopolitical risk indicators from
local Russian newspaper coverage and compare them with indicators built from
English-language coverage of the same events. Identifying shocks in a structural
VAR with sign restrictions, they find that shocks extracted from the local
indicators have significant adverse effects on Russian output, inflation and the
exchange rate, while shocks extracted from the English-language indicators do
not. They control for restricted press freedom by treating state-controlled and
independent Russian outlets separately, and they show that the effects propagate
beyond the sanctions channel, though sanctions worsen the inflationary response.

The methodological content of that paper is a warning with a very wide reach. An
English-language geopolitical risk index is not a neutral measurement of a
conflict; it is a measurement of how one particular media population perceives
that conflict. Where the two coincide, nothing is lost. Where they do not — and
the Russian case is the clearest available demonstration that they need not —
the choice of corpus determines the finding. Their press-freedom control is
adopted directly in Chapter 4, which separates Russian state-controlled from
Russian independent and exile outlets, and it earns its place: Chapter 5 reports
that Russian state media's tone did not move when Russia invaded Ukraine, +0.02
in aggregate and −0.05 on a fixed panel of twenty-four outlets present on both
sides of the event, against −1.66 for Ukrainian media over the same window. An
indicator built from Western coverage would record none of that.

## 2.3 Evaluating a predictive claim

The asset-pricing half of this thesis inherits a second literature, concerned
less with what to measure than with how sceptically to judge a measurement once
it has been regressed on returns. Welch and Goyal (2008) established the
reference point by running the standard set of equity-premium predictors out of
sample against a historical-mean benchmark and finding that most of them fail —
that in-sample significance is a poor guide to out-of-sample performance, and
that predictive regressions are unstable across subsamples in ways in-sample
statistics conceal.

Campbell and Thompson (2008) responded with both a metric and a calibration.
Their out-of-sample R² compares a candidate forecast's mean squared error with
the benchmark's over a common evaluation window, and their argument that
economically meaningful predictability is small — of the order of a few tenths
of a percent at the monthly frequency — has set the scale against which such
claims are now read. Clark and West (2007) supply the correct test when the
candidate model nests the benchmark, as it does whenever a predictor is added to
a historical mean: under the null the larger model estimates parameters that are
truly zero, so its forecast error is inflated by estimation noise, and an
uncorrected comparison is biased against the alternative. Diebold and Mariano
(1995) provide the general equal-predictive-accuracy test for the non-nested
case. Chapter 7 uses Campbell–Thompson R²_OS as the headline metric and
Clark–West as the test, the latter because the specifications there are nested
by construction. Corsi (2009) supplies the volatility benchmark the design
specifies where one is needed — a heterogeneous autoregressive regression of
realized variance on its own daily, weekly and monthly averages, a simple linear
model that is hard to beat and that, unlike the GARCH-X-in-mean specification of
the previous version of this project, does not degenerate numerically. The
out-of-sample evaluation reported in Chapter 7 is of returns.

These tools are what turn the negative results of Chapters 6 and 7 into
findings. Zero of fifty Clark–West rejections is uninformative on its own; it
becomes informative when paired with the simulated power curve of Chapter 7,
which shows that a true out-of-sample R² of 0.5% would have been detected 82% of
the time and 0.2% 43% of the time, against a best observed value of 0.10%.
Predictability across most of the range this literature reports is ruled out in
this sample. That is a bounded claim, and bounding it required exactly the
apparatus above.

## 2.4 The gap

The two strands meet nowhere. The text-based asset-pricing literature has become
sophisticated about *what* it counts — policy uncertainty, implied volatility,
firm-level exposure, threats against acts — and has remained almost entirely
monolingual about *whose* text it counts. The perception literature has shown
that the source of the text is decisive, but has demonstrated it on
macroeconomic aggregates in the economy the risk is about. Nobody has tested the
source-perspective decomposition on asset prices.

This thesis runs that test, and runs it as a mirror image of Bondarenko et al.
(2024). They ask whether local-language perception matters for the economy the
geopolitical risk is *about*; this thesis asks whether it matters for the assets
of the counterparties who arm one side and trade with the other. The two
questions have the same structure and opposite subjects.

| | Bondarenko et al. (2024) | This thesis |
|---|---|---|
| Outcome | Russian macroeconomic aggregates | Western and global defence-equity returns, European gas, realized escalation |
| Perspective split | local Russian versus English-language | three-way: aggressor, victim and third-party investor-facing, with an English-only arm replicating their comparison |
| Whose economy | the country the risk is about | the counterparties who arm one side and trade the other |
| Press-freedom control | state-controlled versus independent Russian media | adopted directly, as a design control rather than a result |
| Evaluation | structural VAR with sign restrictions | pre-registered conditional tests with multiple-testing control, plus out-of-sample forecast evaluation with a power statement |

The answer, given in full in Chapters 6 and 7, is the reverse asymmetry. Local
perception — Ukrainian and Russian, in attention, in tone and in anticipation
structure — adds nothing to defence-equity returns beyond what Western coverage
already carries, while the Western block is detected by the same design on the
same data. This is complementary to Bondarenko et al. rather than a
contradiction of them. Their result and this one both say that an asset or an
economy responds to the perceptions of the agents who hold it: Russian output
moves with what Russian newspapers report, and Western defence equities move
with what Western newspapers report. What is new here is that the second half of
that sentence had never been tested, and that it can now be stated with a
measured bound on how large an effect the test would have found.
