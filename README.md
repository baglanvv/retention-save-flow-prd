# PRD: Automated retention save-flow

A product requirements document for an AI-assisted cancellation flow, written
as a companion to [`churn-reason-eval`](../churn-reason-eval) — the eval
decided what this spec is allowed to promise.

- **Status:** draft for review
- **Author:** Baglan Zharkenov
- **Last updated:** 2026-10-12
- **Eval dependency:** [`churn-reason-eval`](../churn-reason-eval) · held-out test n=48

> **Scope note.** This specifies a feature for a hypothetical EdTech
> subscription, written as a portfolio work sample. Every quantity in
> *Assumptions* is illustrative and labeled as such. No figure here is measured
> from a real platform.

---

## 1. Problem

Learners who cancel tell us why, in free text, on the way out. Nobody reads it
at volume. Two things are lost at once:

1. **Saves we could have made.** A learner who is simply out of time will often
   accept a pause instead of a cancellation. Today they get the same generic
   "sorry to see you go" as everyone else, and we lose revenue we never had to
   lose.
2. **The product signal.** Cancellation text is the most candid feedback the
   company receives, and it currently goes into a table nobody queries.

The failure is not that we lack the data. It is that the data arrives as
unstructured text at a moment when the only possible response is automated.

## 2. Goals and non-goals

**Goals**

- G1 — Route each cancelling learner to the retention action that matches their
  actual reason, automatically, at the moment of cancellation.
- G2 — Turn cancellation text into a weekly structured signal for the
  curriculum and engineering teams.
- G3 — Produce labeled data as a by-product, so the quality bar for automation
  can be raised with evidence rather than opinion.

**Non-goals**

- N1 — **Making cancellation harder.** No extra confirmation steps, no dark
  patterns, no hiding the cancel button. The flow runs *after* the
  cancellation is accepted and honoured.
- N2 — Discounting as a default retention lever. Discounts are one branch of
  eight, gated on reason.
- N3 — Replacing human support. The flow is designed to escalate, not absorb.
- N4 — Classifying anything other than cancellation comments in v1.

## 3. Success metrics

| | Metric | Target | Why this one |
|---|---|---|---|
| **Primary** | Net saves per 100 cancellations | +3 vs. control | The only outcome that pays for the feature |
| **Secondary** | Pause-instead-of-cancel conversion on `time` branch | ≥ 15% | Cheapest save; tests whether routing works at all |
| **Secondary** | Cancellation comments with an actionable label | ≥ 70% | Measures coverage, not correctness |
| **Guardrail** | Discount margin spend per save | ≤ $55 | Catches a classifier that routes everyone to `price` |
| **Guardrail** | Discounts issued to `goal_met` learners | ≤ 2% of discounts | The specific expensive error from the eval |
| **Guardrail** | Support tickets created per 100 flows | no increase | Catches a flow that confuses people |
| **Guardrail** | Cancellation completion time | no increase | Enforces N1 — cancelling must not get slower |

The two guardrails on discounts exist because the eval identified the exact
failure that costs money: `goal_met` misread as `price` hands margin to someone
who already finished and was leaving satisfied.

## 4. What the eval decided

The eval was built to answer "should an LLM classify these comments?" It
returned a different and more useful answer, and this spec is built on it.

| Finding | Consequence for this spec |
|---|---|
| A $0 keyword baseline scores 0.958 on held-out test | v1 ships **rules, not a model** |
| 95% CI [0.860, 0.988] on n=48 — no improvement is detectable | An LLM cannot be *justified* yet, so it is deferred, not rejected |
| Test set is synthetic and the baseline is contaminated by shared authorship | The 0.958 is a **ceiling**, not a forecast — production accuracy will be lower |
| One `price -> unclear` error carried 72% of all regret | Abstention must route to humans, never to a default action |

**Therefore v1 is deliberately unambitious:** rules for the classes they handle
cleanly, abstention everywhere else, humans on the abstentions, and their
labels become the test set that earns the LLM decision in v2.

This is the sequencing that matters. Shipping an LLM first would have bought a
worse-understood system at higher cost, and we would not have been able to tell
whether it was working.

## 5. Solution

### 5.1 Flow

```
Learner confirms cancellation
   |
   v
Cancellation is processed  <-- unconditional, never gated on what follows (N1)
   |
   v
"Before you go, what prompted this?"  [free text, skippable]
   |
   v
Classifier (keyword rules, v1)
   |
   +-- confident label --> matched offer, shown once
   |
   +-- abstains / low signal --> no offer; queued for human review within 48h
```

Three properties worth naming:

- **The cancellation is already done** before any offer appears. The learner
  has their outcome; the offer is a genuine invitation to return, not a toll.
- **One offer, once.** No second attempt, no email follow-up on a declined
  offer.
- **Abstention is a first-class branch**, not an error path. It is expected on
  ~25% of comments and is cheaper than a wrong offer.

### 5.2 Branches

| Label | What the learner is offered | Owner |
|---|---|---|
| `time` | Pause for 1–3 months, one tap, keeps progress | Growth |
| `price` | Cheaper tier, or 40% for 3 months | Growth |
| `content_gap` | Specific alternative track, if one matches; else nothing | Curriculum |
| `technical` | Apology + service credit + bug reference | Engineering |
| `support` | Senior agent reaches out within 24h | Support |
| `goal_met` | **Congratulations + testimonial/referral ask. No discount.** | Growth |
| `competitor` | Nothing offered; logged for competitive intel | Product |
| `unclear` | Nothing offered; queued for human review | Support |

`goal_met` and `competitor` deliberately offer no retention incentive. A
learner who finished is not a lost sale, and discounting them is the clearest
money-losing error available.

### 5.3 When the classifier is wrong

The spec is only as good as its handling of the error cases, so these are
requirements, not notes:

- **R1 — Abstain rather than guess.** Any comment the rules do not match
  confidently gets no offer. Measured: abstention rate is reported weekly, and
  a drop below 15% or above 40% triggers review.
- **R2 — No irreversible action on a prediction.** Nothing in the flow charges,
  refunds, cancels, or alters a subscription based on a label. Labels select
  which *offer* is displayed. The learner's own tap is the only state change.
- **R3 — Discount rate limiting.** A per-day cap on discount offers, so a
  classifier regression cannot give away margin at scale before anyone notices.
- **R4 — Every label is logged with its input** and is human-correctable. The
  correction stream is the v2 training and test data.
- **R5 — Visible escape hatch.** Every branch ends with "talk to a person"
  regardless of label.

R2 is the load-bearing one. It means a misclassification costs us a *wasted
offer*, never a wrong charge or a lost subscription — which is what makes
shipping a 0.958-ceiling classifier acceptable at all.

## 6. Rollout

| Phase | Scope | Gate to advance |
|---|---|---|
| 0 | Shadow mode: classify, log, show nothing | ≥ 500 comments classified; human review of 100 confirms accuracy ≥ 0.85 **on real text** |
| 1 | 10% of cancellations, `time` + `goal_met` branches only | Pause conversion ≥ 25%; zero discounts to `goal_met`; no support-ticket increase |
| 2 | 50%, all eight branches | Primary metric trending positive; discount margin per save ≤ $55 |
| 3 | 100% + weekly signal report to curriculum/engineering | — |
| 4 | Revisit the LLM with the real labeled set from phases 0–3 | ≥ 1,500 real labeled rows per arm — what `churn-reason-eval/src/power.py` says is needed to resolve a 2-point gain near 95% |

Phase 0 is the phase that matters most and is the one most often skipped.
**The eval's accuracy figure is measured on synthetic text I wrote myself.
Phase 0 is where that number meets reality**, and the 0.85 gate is set well
below the synthetic 0.958 precisely because the drop is expected.

Phase 1 starts with `time` and `goal_met` because they are the cheapest correct
action and the most expensive wrong one. If the routing logic is broken, those
two branches reveal it at the lowest cost.

## 7. Assumptions

**All illustrative. These are the inputs a real version of this doc would pull
from the warehouse, and every downstream number inherits their uncertainty.**

| Assumption | Value used | How to replace it |
|---|---|---|
| Monthly cancellations | 1,200 | Warehouse query |
| Comment completion rate | 55% | Instrument the existing flow |
| Subscription LTV | $480 (12 × $40) | Finance |
| Save rate, `time` branch | 18% | Phase 1 measurement |
| Save rate, `price` branch | 12% | Phase 1 measurement |
| Share of saves who would have returned anyway | 25% | Holdout — see open question 1 |
| Discount cost per save | $48 | Finance |

`python3 sensitivity.py` runs the model behind these, so a reviewer can see
where the case breaks instead of taking a headline on trust. Base case:

```
base          saves  37  /100 3.1  retained $17,712  cost $5,143  net $12,569
```

Three things that grid shows, two of them uncomfortable:

1. **Routing accuracy is not the bottleneck.** Moving it from 0.958 to 0.60
   changes net from $14.8k to $7.4k. Moving the counterfactual-return rate from
   0% to 75% changes net from $18.5k to $0.8k. **The classifier is the part of
   this system I understand best and the part that matters least** — which is
   further reason not to spend on an LLM for v1.
2. **The case survives a 75% haircut on every save rate and no more.** Below
   ~25% of assumed rates it goes negative.
3. An earlier draft of this model used the eval's original save rates
   (0.35–0.55) and produced 12.7 saves per 100 and a $60k/month net. That was
   not a stretch target, it was an error, and it is the reason both this doc
   and the eval now carry deliberately pessimistic rates.

## 8. Open questions

1. **Does the pause offer cannibalise saves we would have made anyway?** A
   learner who would have resubscribed in two months now pauses and pays
   nothing in between. The model assumes 25% of saves are not ours to claim;
   at 75% the feature is worth ~$800/month and is not worth building. **This is
   the single most important unknown in the document** and it needs a holdout
   measuring net revenue, not saves.
2. **Does `goal_met` deserve a referral *program*** rather than a one-off ask?
   Out of scope here, plausibly worth more than the entire save-flow.
3. **Is the Russian-language branch viable at v1?** The eval's RU subset is 9
   held-out rows — far too few to claim anything. Phase 0 should report RU
   accuracy separately before any RU learner sees an automated offer.
4. **Who owns the weekly signal report** once the novelty wears off? A report
   with no owner stops being read by month three.

## 9. What I am least sure about

The weakest link is not the classifier, it is the assumption that a
well-matched offer changes a cancellation decision at all. The sensitivity grid
agrees: accuracy barely moves the outcome, and the counterfactual rate moves it
enormously. By the time someone has clicked
cancel, the decision is usually made; save-flow literature is full of
single-digit conversion. The `time` branch is the one I believe in, because a
pause asks for no new commitment and resolves the actual stated blocker.

If I had to bet on one thing in this spec surviving contact with real data, it
would be the pause offer, and if I had to bet on one thing dying, it would be
the `content_gap` branch — recommending another course to someone who just told
us our courses were inadequate is a hard sell that I would cut from v1 if
scoping pressure demanded it.
