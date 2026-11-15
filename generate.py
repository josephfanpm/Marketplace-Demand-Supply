"""
Synthetic data + analysis for the marketplace supply/demand map.

Everything here is simulated. No real company, market, facility or worker data is used.
The simulation exists so the method can be shown end to end:

  1. Simulate a shift marketplace across the 48 continental states and DC: markets with
     different worker supply, shifts with different traits (pay vs local rate, posting lead
     time, weekend, night, approval required, multi-slot), and an outcome for every posted slot.
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
STATES = ["AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD",
          "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
          "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY"]
BIG_STATES = ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN"]  # get a second market
TOWNS = ["Northvale", "Ashford", "Brookmere", "Cedar Falls", "Dunmore", "Eastport", "Fairhaven", "Glenwood", "Harbor City",
         "Ironton", "Juniper Bay", "Kingsbridge", "Lakemont", "Millbrook", "Newcastle", "Oakridge", "Pinecrest", "Queensport",
         "Riverton", "Stonegate", "Thornbury", "Upton", "Valemont", "Westfield", "Yorkfield", "Zephyr Hills", "Amberly",
         "Bellhaven", "Crestwood", "Dovercourt", "Elmhurst", "Foxborough", "Granite Bend", "Hollis Creek", "Ivy Ridge",
         "Jasper Point", "Kestrel Lake", "Linden Hill", "Maple Ferry", "North Fork", "Orchard Glen", "Pike Hollow",
         "Quarry Mill", "Red Mesa", "Silver Pines", "Tall Oaks", "Union Grove", "Vista Del Sol", "Willow Run", "Ashby Falls",
         "Birch Harbor", "Clearwater Bend", "Deer Crossing", "Elk Prairie", "Fern Valley", "Gold Ridge", "Hawk Hollow",
         "Indigo Springs", "Jade Harbor", "Knoll Park", "Lark Meadow", "Mesa Verde Junction", "Nettle Creek", "Opal Bay"]

# "True" world: effects of shift traits on the log-odds a posted slot gets worked.
TRUE = {"intercept": 0.9, "pay_low": -0.9, "pay_high": 0.15, "late_post": -0.8, "weekend": -0.25, "night": -0.1,
        "approval": -0.6, "multi_slot": 0.2, "license_rn": -0.4}
FEATURES = ["pay_low", "pay_high", "late_post", "weekend", "night", "approval", "multi_slot", "license_rn"]
LOST_BEFORE = ["open", "deleted_late", "applied_not_booked", "slot_removed"]


def make_markets():
    states = STATES + BIG_STATES
    towns = rng.permutation(TOWNS)[:len(states)]
    markets = []
    for i, (st, town) in enumerate(zip(states, towns)):
        markets.append(dict(
            id=i, name=f"{town}, {st}", state=st,
            size=float(rng.lognormal(6.3 + np.log(10), 0.7)),              # weekly posted hours scale
            supply=float(rng.normal(0, 0.55)),                            # market supply strength (hidden)
            decline=float(rng.choice([0.0, -0.02, -0.045], p=[0.5, 0.2, 0.3])),  # some markets lose supply over time
            callout=float(np.clip(rng.normal(0.16, 0.07), 0.03, 0.4)),    # share of booked slots called out
            approval_share=float(rng.choice([0.05, 0.1, 0.6], p=[0.6, 0.3, 0.1])),
            late_share=float(np.clip(rng.normal(0.25, 0.12), 0.02, 0.7)),
            low_pay_share=float(np.clip(rng.normal(0.2, 0.15), 0, 0.9))))
    return markets


def simulate(markets):
    """Vectorised per market-week. Returns column arrays, one entry per posted 8-hour slot."""
    cols = {k: [] for k in ["market", "week", *FEATURES, "outcome", "worked"]}
    for m in markets:
        for wk in range(WEEKS):           # wk 0 = oldest
            n = int(rng.poisson(m["size"] / 8 * (1 + 0.006 * wk)))      # posted slots that week (8h each)
            if n == 0:
                continue
            f = {
                "pay_low": rng.random(n) < m["low_pay_share"],
                "late_post": rng.random(n) < m["late_share"],
                "weekend": rng.random(n) < 2 / 7,
                "night": rng.random(n) < 0.3,
                "approval": rng.random(n) < m["approval_share"],
                "multi_slot": rng.random(n) < 0.35,
                "license_rn": rng.random(n) < 0.2,
            }
            f["pay_high"] = ~f["pay_low"] & (rng.random(n) < 0.15)
            x = TRUE["intercept"] + sum(TRUE[k] * f[k] for k in FEATURES) + m["supply"] + m["decline"] * wk
            p_book = 1 / (1 + np.exp(-x))
            outcome = np.full(n, "worked", dtype=object)
            early = rng.random(n) < 0.06
            not_booked = ~early & (rng.random(n) > p_book)
            outcome[not_booked] = rng.choice(LOST_BEFORE, size=not_booked.sum(), p=[0.55, 0.25, 0.08, 0.12])
            outcome[early] = "deleted_early"
            booked = ~early & ~not_booked
            u = rng.random(n)
            outcome[booked & (u < m["callout"])] = "called_out"
            outcome[booked & (u >= m["callout"]) & (u < m["callout"] + 0.08)] = "cancelled"
            outcome[booked & (u >= m["callout"] + 0.08) & (u < m["callout"] + 0.095)] = "no_show"
            worked = np.where(outcome == "worked", 8 - np.maximum(rng.normal(0.35, 0.3, n), 0), 0.0)
            cols["market"].append(np.full(n, m["id"])); cols["week"].append(np.full(n, wk))
            for k in FEATURES:
                cols[k].append(f[k])
            cols["outcome"].append(outcome); cols["worked"].append(worked)
    return {k: np.concatenate(v) for k, v in cols.items()}


def main():
    markets = make_markets()
    d = simulate(markets)
    feats = np.column_stack([d[k] for k in FEATURES]).astype(float)
    worked_frac = d["worked"] / 8
    wk, mid, outcome = d["week"], d["market"], d["outcome"]

    # Expected fill from shift traits only, fitted on the latest 8 weeks.
    recent = wk >= WEEKS - 8
    X, y = feats[recent], worked_frac[recent]
    model = LogisticRegression(C=1e6, max_iter=2000).fit(np.r_[X, X], np.r_[np.ones(len(X)), np.zeros(len(X))], sample_weight=np.r_[y, 1 - y])
    p = model.predict_proba(feats)[:, 1]

    weekly = [{"week": w - WEEKS + 1, "fill_pct": round(100 * worked_frac[wk == w].mean(), 1), "expected_pct": round(100 * p[wk == w].mean(), 1)}
              for w in range(WEEKS)]
    nat_exp = p[recent].mean()
    hrs_per_worker = 14.0     # assumed weekly hours per worker for the demo
    out_markets = []
    for m in markets:
        s = recent & (mid == m["id"])
        posted = int(s.sum())                         # slots per week over 8 weeks x 8 hours / 8 weeks = slots
        fill, exp = worked_frac[s].mean(), p[s].mean()
        vs = 100 * (fill - exp)
        lost_open = int((outcome[s] == "open").sum())
        lost_rel = int(np.isin(outcome[s], ["called_out", "no_show"]).sum())
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
            "market": m["name"], "state": m["state"], "posted_hrs_wk": posted, "fill_pct": round(100 * fill, 1), "expected_pct": round(100 * exp, 1),
            "vs_expected_pts": round(vs, 1), "status": status,
            "workers_short": round(gap_hrs / hrs_per_worker) if status == "Recruit workers" else 0,
            "late_post_pct": round(100 * feats[s][:, 2].mean()), "approval_pct": round(100 * feats[s][:, 5].mean()), "low_pay_pct": round(100 * feats[s][:, 0].mean()),
        })

    flow = {k: int((outcome[recent] == k).sum()) for k in LOST_BEFORE + ["deleted_early", "called_out", "cancelled", "no_show"]}
    flow["posted"] = int(recent.sum()); flow["worked"] = round(float(worked_frac[recent].sum()))
    flow["short"] = round(float(((outcome[recent] == "worked") * (8 - d["worked"][recent])).sum() / 8))
    coef = dict(zip(FEATURES, np.round(model.coef_[0], 2).tolist()))
    data = {"note": "Synthetic data. Every market, number and name is simulated.", "national_fill_pct": round(100 * worked_frac[recent].mean(), 1),
            "national_expected_pct": round(100 * nat_exp, 1), "weekly": weekly, "markets": sorted(out_markets, key=lambda r: r["vs_expected_pts"]),
            "flow": flow, "model": {"fitted_coefficients": coef, "true_coefficients": {k: v for k, v in TRUE.items() if k != "intercept"}}}
    os.makedirs("docs", exist_ok=True)
    json.dump(data, open("docs/data.json", "w"), indent=1)
    print(f"{len(outcome):,} simulated slots in {len(markets)} markets across {len({m['state'] for m in markets}) - 1} continental states and DC; "
          f"national fill {data['national_fill_pct']}% vs expected {data['national_expected_pct']}%")
    print("status counts:", {s: sum(m["status"] == s for m in out_markets) for s in sorted({m["status"] for m in out_markets})})


if __name__ == "__main__":
    main()
