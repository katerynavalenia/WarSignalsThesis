# Note to the supervisor — draft to send with the thesis

The v3 plan specified an informational note to be sent early. It never was. What
follows is written for sending **with the completed draft** instead, which is the
situation that actually obtains.

Two notes on tone. It reports results rather than asking for guidance, because
there is no longer time to act on a reply. And it does not apologise for the null:
the power statement is what makes it a finding, and the five retractions are the
reason it should be believed.

---

## Draft

> Dear Thomas,
>
> Thank you for the review — acting on it changed the project substantially, and
> the third comment in particular turned out to matter more than I think either
> of us expected.
>
> **On the sentiment methodology (comment 3).** Writing the fuller description
> you asked for uncovered a measurement error rather than a documentation gap.
> The previous indicators were built from GDELT's version 1.0 stream, which is
> effectively English-only — on 1 March 2025 it contains seven Russian-domain and
> twenty-one Ukrainian-domain articles out of 60,690 — and national groups were
> assigned for 88.6% of articles by the country most frequently *mentioned*
> rather than by the publisher. "Russian sentiment" was therefore the tone of
> English-language coverage about Russia. I have rebuilt the indicators from
> GDELT's translingual archive, classifying by publisher country, language and
> ownership. The rebuilt ecosystems are genuinely distinct where the previous
> ones were near-duplicates: Ukrainian against native-English attention now
> correlates at 0.05.
>
> **On the sample (comment 1).** You were right that the September 2022 start was
> the binding limitation, and it was set by the air-attack dataset rather than by
> GDELT. The sample now runs from 18 February 2015 — the first day of the
> translingual archive — to May 2026: 4,027 days of coverage, roughly three
> times the reviewed version on matched units (2,837 trading days against 931),
> with the February 2022 period inside it.
>
> **On the forecasting tests (comment 4).** These are now Campbell–Thompson
> out-of-sample R² with Clark–West tests, with Benjamini–Hochberg correction
> across the grid. I use Clark–West rather than Diebold–Mariano for the nested
> comparisons, since the models nest the benchmark and the DM statistic is not
> valid there; DM is implemented and used where the comparison is non-nested. The
> more useful addition is a simulated power curve: with 1,855 out-of-sample
> observations the test detects an R²_OS of 0.5% at 82% power and 0.2% at 43%.
> The best observed is 0.11% and no test survives correction, so the null is
> bounded rather than merely observed.
>
> **On Bondarenko et al. (comment 5).** It became the methodological anchor. They
> find local-language geopolitical-risk shocks move the Russian economy while
> English-language ones do not. This thesis runs the mirror test on the
> counterparty's assets and finds the reverse asymmetry: Western defence equities
> price the Western narrative, and local-language perception adds nothing beyond
> it — in coverage volume, in tone, or in the anticipation-versus-realization
> structure of that coverage.
>
> **What I should flag.** The headline result is a null, and I have tried hard to
> break it. It holds for defence equities, for European natural gas — which I
> added precisely because defence equities are a weak testbed, since the link
> from Russian reporting to a US contractor runs entirely through Western
> investors — and for realized escalation as a non-market outcome. In each case
> a positive control confirms the design detects Western media where Western
> media matter.
>
> Along the way five apparently significant results did not survive: two to an
> omitted European market control, one to adding a held-out window to a truncated
> sample, one to pre-registered replication on a larger sample, and one to
> out-of-sample testing after being significant in both halves of the in-sample
> period. I have written these up rather than removed them, because the sequence
> is the most useful methodological result the project produced.
>
> One limitation I want to name directly: the hand-labelled precision audit of
> the outlet classification was not completed, so the classification is validated
> externally — against the published GPR index and on known event dates — but not
> by reading articles. A register error I found by a robustness check rather than
> by validation is, I think, the strongest argument for completing it.
>
> The descriptive chapter you suggested is Chapter 5, and it contains what I
> expect will be the most quoted result: Russian state media's tone did not move
> when Russia invaded Ukraine — a shift of +0.02, and −0.05 on a fixed panel of
> twenty-four outlets present on both sides of the invasion — while Ukrainian
> media's fell by 1.66 points.
>
> Best regards,
> Kateryna

---

## Notes before sending

- Send **with** the draft attached, not before it.
- Do not raise the framing question. The question sentence moved from "do war
  signals forecast defence equities" to "whose perception is priced", but that
  followed directly from comments 3 and 5 — classifying by publisher is what
  creates a "whose" question, and Bondarenko is about exactly that. The
  forecasting question is still answered, in Chapter 7, with the tests he asked
  for. Nothing was substituted; a second question was added.
- The one thing he may reasonably press on is the missing precision audit. The
  answer is that it is the first item of remaining work, and that `dw.com` sitting
  misclassified in the Russian-independent register — caught by a fixed-panel
  robustness run rather than by validation — is the evidence that it matters.
