"""
Synthetic data + analysis for the marketplace supply/demand map.

Everything here is simulated. No real company, market, facility or worker data is used.
The simulation exists so the method can be shown end to end:

  1. Simulate a shift marketplace: markets with different worker supply, shifts with
     different traits (pay vs local rate, posting lead time, weekend, night, approval
     required, multi-slot), and an outcome for every posted slot.
  2. Fit an "expected fill" model on shift traits only (no supply inputs).
  3. Compare each market's actual fill with its expected fill to decide whether the
     problem is the shifts (fix the shifts) or the market (recruit / reliability).
  4. Write docs/data.json for the static demo page.

Run:  python generate.py   (needs numpy and scikit-learn)
"""
import json
import os

import numpy as np
from sklearn.linear_model import LogisticRegression

rng = np.random.default_rng(7)
WEEKS = 26
NAMES = [
    "Northvale", "Ashford", "Brookmere", "Cedar Falls", "Dunmore", "Eastport", "Fairhaven", "Glenwood",
    "Harbor City", "Ironton", "Juniper Bay", "Kingsbridge", "Lakemont", "Millbrook", "Newcastle", "Oakridge",
    "Pinecrest", "Queensport", "Riverton", "Stonegate", "Thornbury", "Upton", "Valemont", "Westfield",
    "Yorkfield", "Zephyr Hills", "Amberly", "Bellhaven", "Crestwood", "Dovercourt", "Elmhurst", "Foxborough",
]
LICENSES = ["Aide", "Practical nurse", "Registered nurse"]

# "True" world: effects of shift traits on the log-odds a posted slot gets worked.
TRUE = {"intercept": 0.9, "pay_low": -0.9, "pay_high": 0.15, "late_post": -0.8, "weekend": -0.25, "night": -0.1,
        "approval": -0.6, "multi_slot": 0.2, "license_rn": -0.4}


def simulate():
    markets = []
    for i, name in enumerate(NAMES):
        size = float(rng.lognormal(6.3, 0.7))                       # weekly posted hours scale
        supply = float(rng.normal(0, 0.55))                          # market supply strength (hidden)
        decline = float(rng.choice([0.0, -0.02, -0.045], p=[0.5, 0.2, 0.3]))  # some markets lose supply over time
        callout = float(np.clip(rng.normal(0.16, 0.07), 0.03, 0.4))  # share of booked slots called out
        approval_share = float(rng.choice([0.05, 0.1, 0.6], p=[0.6, 0.3, 0.1]))
        late_share = float(np.clip(rng.normal(0.25, 0.12), 0.02, 0.7))
        low_pay_share = float(np.clip(rng.normal(0.2, 0.15), 0, 0.9))
        markets.append(dict(id=i, name=name, size=size, supply=supply, decline=decline, callout=callout,
                            approval_share=approval_share, late_share=late_share, low_pay_share=low_pay_share))
    rows = []
    for m in markets:
        for wk in range(WEEKS):           # wk 0 = oldest
            n = rng.poisson(m["size"] / 8 * (1 + 0.006 * wk))       # posted slots that week (8h each)
            for _ in range(n):
                pay_low = rng.random() < m["low_pay_share"]
                pay_high = (not pay_low) and rng.random() < 0.15
                late = rng.random() < m["late_share"]
                weekend = rng.random() < 2 / 7
                night = rng.random() < 0.3
                approval = rng.random() < m["approval_share"]
                multi = rng.random() < 0.35
                rn = rng.random() < 0.2
                x = (TRUE["intercept"] + TRUE["pay_low"] * pay_low + TRUE["pay_high"] * pay_high + TRUE["late_post"] * late
                     + TRUE["weekend"] * weekend + TRUE["night"] * night + TRUE["approval"] * approval
                     + TRUE["multi_slot"] * multi + TRUE["license_rn"] * rn + m["supply"] + m["decline"] * wk)
                p_book = 1 / (1 + np.exp(-x))
                # Outcome for the slot.
                if rng.random() < 0.06:
                    outcome = "deleted_early"
                elif rng.random() > p_book:
                    outcome = rng.choice(["open", "deleted_late", "applied_not_booked", "slot_removed"], p=[0.55, 0.25, 0.08, 0.12])
                elif rng.random() < m["callout"]:
                    outcome = "called_out"
                elif rng.random() < 0.08:
                    outcome = "cancelled"
                elif rng.random() < 0.015:
                    outcome = "no_show"
                else:
                    outcome = "worked"
                worked = 8 - max(rng.normal(0.35, 0.3), 0) if outcome == "worked" else 0.0
                rows.append((m["id"], wk, pay_low, pay_high, late, weekend, night, approval, multi, rn, outcome, worked))
    return markets, rows


def fit_expected(rows):
    """Expected fill from shift traits only, fitted on the latest 8 weeks."""
    feats = np.array([[r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]] for r in rows], dtype=float)
    worked_frac = np.array([r[11] / 8 for r in rows])
    recent = np.array([r[1] >= WEEKS - 8 for r in rows])
    X = feats[recent]; y = worked_frac[recent]
    model = LogisticRegression(C=1e6, max_iter=2000).fit(np.r_[X, X], np.r_[np.ones(len(X)), np.zeros(len(X))], sample_weight=np.r_[y, 1 - y])
    return model, feats, worked_frac


def main():
    markets, rows = simulate()
    model, feats, worked_frac = fit_expected(rows)
    p = model.predict_proba(feats)[:, 1]
    wk = np.array([r[1] for r in rows]); mid = np.array([r[0] for r in rows]); outcome = np.array([r[10] for r in rows])

    weekly = []
    for w in range(WEEKS):
        s = wk == w
        weekly.append({"week": w - WEEKS + 1, "fill_pct": round(100 * worked_frac[s].mean(), 1), "expected_pct": round(100 * p[s].mean(), 1)})

    recent = wk >= WEEKS - 8
    nat_fill = worked_frac[recent].mean(); nat_exp = p[recent].mean()
    hrs_per_worker = 14.0     # assumed weekly hours per worker for the demo
    out_markets = []
    for m in markets:
        s = recent & (mid == m["id"])
        posted = s.sum() * 8 / 8; fill = worked_frac[s].mean(); exp = p[s].mean()
        vs = 100 * (fill - exp)
        lost_open = (outcome[s] == "open").sum() * 8 / 8
        lost_rel = np.isin(outcome[s], ["called_out", "no_show"]).sum() * 8 / 8
        if posted < 40:
            status = "Too little data"
        elif vs <= -8 and lost_rel > lost_open:
            status = "Improve reliability"
        elif vs <= -8:
            status = "Recruit workers"
        elif vs >= 8:
            status = "Spare capacity"
        elif 100 * (exp - nat_exp) <= -4:
            status = "Fix shifts"
        else:
            status = "Healthy"
        gap_hrs = max(exp - fill, 0) * posted
        out_markets.append({
            "market": m["name"], "posted_hrs_wk": round(posted), "fill_pct": round(100 * fill, 1), "expected_pct": round(100 * exp, 1),
            "vs_expected_pts": round(vs, 1), "status": status,
            "workers_short": round(gap_hrs / hrs_per_worker) if status == "Recruit workers" else 0,
            "late_post_pct": round(100 * feats[s][:, 2].mean()), "approval_pct": round(100 * feats[s][:, 5].mean()), "low_pay_pct": round(100 * feats[s][:, 0].mean()),
        })

    flow = {k: round(float((outcome[recent] == k).sum() * 8 / 8)) for k in
            ["open", "deleted_late", "deleted_early", "applied_not_booked", "slot_removed", "called_out", "cancelled", "no_show"]}
    flow["posted"] = round(float(recent.sum() * 8 / 8)); flow["worked"] = round(float(worked_frac[recent].sum() * 8 / 8))
    flow["short"] = round(float(((outcome[recent] == "worked") * (8 - worked_frac[recent] * 8)).sum() / 8))
    coef = dict(zip(["pay_low", "pay_high", "late_post", "weekend", "night", "approval", "multi_slot", "license_rn"], np.round(model.coef_[0], 2).tolist()))
    data = {"note": "Synthetic data. Every market, number and name is simulated.", "national_fill_pct": round(100 * nat_fill, 1),
            "national_expected_pct": round(100 * nat_exp, 1), "weekly": weekly, "markets": sorted(out_markets, key=lambda r: r["vs_expected_pts"]),
            "flow": flow, "model": {"fitted_coefficients": coef, "true_coefficients": {k: v for k, v in TRUE.items() if k != "intercept"}}}
    os.makedirs("docs", exist_ok=True)
    json.dump(data, open("docs/data.json", "w"), indent=1)
    print(f"{len(rows):,} simulated slots; national fill {data['national_fill_pct']}% vs expected {data['national_expected_pct']}%")
    print("status counts:", {s: sum(m["status"] == s for m in out_markets) for s in sorted({m["status"] for m in out_markets})})


if __name__ == "__main__":
    main()
