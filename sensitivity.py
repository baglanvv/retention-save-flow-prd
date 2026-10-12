"""Sensitivity of the save-flow business case to the assumptions in section 7.

The PRD's headline (+4 saves per 100 cancellations, ~$23k/mo retained) rests on
save rates that are guesses. This prints the scenario grid so a reviewer can
see where the case breaks instead of taking the headline on trust.

  python3 sensitivity.py

Stdlib only.
"""

# --- Section 7 assumptions -------------------------------------------------
# LTV, ACTION_COST and BASE_SAVE_RATE deliberately duplicate the constants in
# churn-reason-eval/src/score.py rather than importing them, so this repo
# stands alone when cloned. They MUST stay in sync - the two documents share
# one business model, and they drifted once already during drafting.
CANCELLATIONS_PER_MONTH = 1200
COMMENT_RATE = 0.55          # share who leave any text
LTV = 480.0
DISCOUNT_COST = 48.0         # cost of one price-branch save offer accepted

# Share of commented cancellations falling in each class. Illustrative - this
# is the single most load-bearing unmeasured input after the save rates.
MIX = {
    "time": 0.20, "price": 0.20, "content_gap": 0.15, "goal_met": 0.10,
    "technical": 0.10, "support": 0.10, "competitor": 0.08, "unclear": 0.07,
}

# Cost of the action per learner routed to that branch (not per save).
ACTION_COST = {
    "time": 2.0, "price": DISCOUNT_COST, "content_gap": 12.0, "goal_met": 1.0,
    "technical": 40.0, "support": 25.0, "competitor": 12.0, "unclear": 8.0,
}

# Share of CORRECTLY-ROUTED learners in each branch who accept the offer and
# stay. Published save-flow conversion is single-digit to low-double-digit, so
# an earlier draft of this model using 0.35-0.55 was not defensible - it
# produced a 12.7% overall save rate and a $60k/mo net, which is a fantasy.
# These are deliberately pessimistic.
BASE_SAVE_RATE = {
    "time": 0.18,        # pause asks for no new money - the best of a weak set
    "price": 0.12,
    "content_gap": 0.04, # "try another course" after "your courses were bad"
    "goal_met": 0.0,     # nothing to save
    "technical": 0.08,
    "support": 0.10,
    "competitor": 0.02,
    "unclear": 0.03,
}

# Share of apparent saves who would have resubscribed anyway. The flow gets
# credit it did not earn without this. PRD open question #1.
COUNTERFACTUAL_RETURN = 0.25

# Branches where the cost is only incurred when the offer is ACCEPTED
# (money moves on acceptance). Elsewhere the cost is staff time, paid per case.
COST_ON_ACCEPTANCE_ONLY = {"price", "technical"}

# Classifier does not route everyone correctly. A wrong route wastes the action
# cost and saves nobody. 0.958 is the synthetic ceiling; phase 0 gates at 0.85.
ROUTING_ACCURACY = 0.85
# ---------------------------------------------------------------------------

assert abs(sum(MIX.values()) - 1.0) < 1e-9, "MIX must sum to 1"


def model(save_rates, accuracy=ROUTING_ACCURACY,
          counterfactual=COUNTERFACTUAL_RETURN):
    commented = CANCELLATIONS_PER_MONTH * COMMENT_RATE
    gross_saves = 0.0
    cost = 0.0
    for cls, share in MIX.items():
        n = commented * share
        correct = n * accuracy          # correctly routed
        wrong = n * (1 - accuracy)      # misrouted: wrong remedy, no save
        accepted = correct * save_rates[cls]
        gross_saves += accepted

        if cls in COST_ON_ACCEPTANCE_ONLY:
            # Only the accepted offers cost money. A misrouted learner may also
            # accept a discount they did not need, which is the margin leak the
            # PRD guardrails watch for.
            cost += accepted * ACTION_COST[cls]
            cost += wrong * save_rates[cls] * ACTION_COST[cls]
        else:
            cost += (correct + wrong) * ACTION_COST[cls]

    net_saves = gross_saves * (1 - counterfactual)
    retained = net_saves * LTV
    return {
        "gross_saves": gross_saves,
        "saves": net_saves,
        "saves_per_100_cancellations": 100 * net_saves / CANCELLATIONS_PER_MONTH,
        "retained_ltv": retained,
        "action_cost": cost,
        "net": retained - cost,
    }


def show(name, r):
    print(f"  {name:<34} saves {r['saves']:>5.0f}  "
          f"/100 {r['saves_per_100_cancellations']:>4.1f}  "
          f"retained ${r['retained_ltv']:>8,.0f}  "
          f"cost ${r['action_cost']:>7,.0f}  net ${r['net']:>9,.0f}")


if __name__ == "__main__":
    base = dict(BASE_SAVE_RATE)
    print("Base case (section 7 assumptions, routing accuracy 0.85):")
    show("base", model(base))

    print("\nSensitivity on the 'time' branch - the PRD's main bet:")
    for rate in (0.25, 0.18, 0.12, 0.08, 0.04):
        s = dict(base); s["time"] = rate
        show(f"time save rate = {rate:.2f}", model(s))

    print("\nAll save rates haircut by a constant factor:")
    for f in (1.0, 0.75, 0.5, 0.33, 0.25):
        s = {k: v * f for k, v in base.items()}
        show(f"save rates x {f:.2f}", model(s))

    print("\nRouting accuracy (save rates at base):")
    for acc in (0.958, 0.90, 0.85, 0.75, 0.60):
        show(f"accuracy = {acc:.3f}", model(base, accuracy=acc))

    print("\nCounterfactual-return sensitivity (how much credit is not ours):")
    for cf in (0.0, 0.25, 0.50, 0.75):
        show(f"counterfactual = {cf:.0%}", model(base, counterfactual=cf))

    print("\nBreak-even search on a uniform save-rate haircut:")
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if model({k: v * mid for k, v in base.items()})["net"] > 0:
            hi = mid
        else:
            lo = mid
    print(f"  net turns negative below ~{hi:.0%} of the assumed save rates")
    print(f"  i.e. the case survives a {1-hi:.0%} haircut and no more")
