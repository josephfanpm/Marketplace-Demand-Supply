# Case study: from "where do we buy ads?" to "why is this hour unfilled?"

This is the long version of the [README](../README.md): how the Market Map changed as I learned what was actually going wrong, and why each design decision landed where it did. Every figure in the [demo](https://josephfanpm.github.io/Marketplace-Demand-Supply/) is scrambled; this document describes findings only in general terms.

## Contents

1. [The ask](#1-the-ask)
2. [Learning from other marketplaces](#2-learning-from-other-marketplaces)
3. [The finding that changed the brief](#3-the-finding-that-changed-the-brief)
4. [Is "nurses short" real? Validating the supply signal](#4-is-nurses-short-real-validating-the-supply-signal)
5. [Shift quality: pay, timing and approval](#5-shift-quality-pay-timing-and-approval)
6. [Using models without over-trusting them](#6-using-models-without-over-trusting-them)
7. [Forecasting supply and demand](#7-forecasting-supply-and-demand)
8. [Designing for each team, and for executives](#8-designing-for-each-team-and-for-executives)
9. [Making it cheap, fast and shared](#9-making-it-cheap-fast-and-shared)
10. [What the data couldn't answer yet](#10-what-the-data-couldnt-answer-yet)
11. [What I'd do differently](#11-what-id-do-differently)

## 1. The ask

The marketplace grows market by market: sales signs facilities, then marketing and recruiting build up a local nurse supply. Marketing wanted a map showing where new facilities were opening and where nurse supply was thin, so paid ads could ramp up in the right places.

The first version did exactly that: a US map of metro areas, sized by demand and colored by how short each looked. It was quick to build and easy to read. It also rested on an assumption nobody had tested: that a market filling poorly is a market short of nurses.

## 2. Learning from other marketplaces

Before going further I looked at how other two-sided marketplaces present supply and demand to operators and executives:

| Source | Pattern | What I took |
|---|---|---|
| a16z, Point Nine on liquidity | Fill rate (match rate) is the headline metric, and it should be measured per market, not only nationally | Fill rate by metro area, ranked |
| Ride-hailing operations | Heatmaps of unmet demand | A map, kept to a few plain categories for executives |
| Staffing marketplaces (Qwick, DirectShifts benchmarks) | Fill rate by market, with industry benchmarks | Market ranking and comparisons |
| Lenny's Newsletter on constrained marketplaces | First work out which side is the constraint | An explicit "short of supply" vs "spare capacity" label |
| RevOps capacity planning | Separate "not enough supply" from "supply not converted" | The idea that became expected vs actual fill |

Shift staffing differs from ride-hailing in ways that shaped the design. Demand is scheduled days ahead, so how early a shift is posted matters. Booking can need a manager's approval. And a booked shift can still be lost through a callout, then won back by a replacement. So time-of-booking and outcome matter as much as geography.

## 3. The finding that changed the brief

I broke every unfilled hour down by what actually happened to the slot:

- **Before booking:** nobody applied, the facility deleted it close to the start, the facility removed slots, applicants were declined or never confirmed.
- **After booking:** the nurse called out, didn't show, or was cancelled by the facility.

Only part of the loss was a genuine supply shortage. Facility practices (late deletions, late posting, approval steps, unconfirmed applicants) and nurse callouts together accounted for more. Existing markets, not new ones, held most of the lost hours.

So the tool's users changed. A map for marketing became views for five teams, each with an owner for its share of lost hours:

| Lost hours from… | Owner |
|---|---|
| Too few nurses for shifts that should fill | Recruiting, marketing, paid ads |
| Callouts and no-shows | Nurse operations |
| Late deletions, removed slots, cancellations, unconfirmed applicants, approval steps, late posting, low pay | Client success |
| Spare capacity (more nurses than shifts) | Sales / account managers |

## 4. Is "nurses short" real? Validating the supply signal

The obvious supply signal is "active nurses near the facility". Before trusting it, I tested whether more nearby nurses actually raise fill. I compared the same facility week to week, so facility quality couldn't explain the result.

- In thin markets, more nearby nurses clearly raised fill.
- Above a modest number of nearby nurses, the effect flattened out.

That meant "nurses short" should only be counted where supply is genuinely thin. A second signal turned out stronger than headcount: **familiarity**. Nurses overwhelmingly book at facilities they've worked at before, so a facility with many nearby nurses who've never worked there behaves like a thin market. That pointed to a cheaper fix than recruiting: get nearby nurses a first shift there.

## 5. Shift quality: pay, timing and approval

The next challenge was "what if those unfilled shifts were just bad shifts?" Testing it:

- **Pay** only hurt meaningfully when it was well below the local rate for that license; a little below behaved like market rate.
- **Posting late** (within about 12 hours of the start) sharply lowered fill.
- **Requiring a manager's approval** to book lowered fill a lot compared with instant book, even at the same facility and pay. Approval-required shifts were a large share of the hours that "nurses passed over at normal pay".

These are fixable by client success, not by recruiting. That's what made "Fix shifts" a separate status.

## 6. Using models without over-trusting them

I built three models on the warehouse, each tested on later weeks it never saw:

| Model | Predicts | How it's used now |
|---|---|---|
| Fill likelihood | Whether a posted slot gets worked, from its traits | **As a benchmark** (expected fill), not as a cause splitter |
| Callout risk | Whether a booking will be called out | Kept for operations tools (individual-level) |
| Nurse supply | Whether a recently active nurse works in the next 4 weeks | Supply forecast and retention targeting (needs scheduled scoring) |

My first use of the fill model split every lost hour into causes ("this many hours lost to low pay, this many to late posting"). It looked precise. Then I reviewed it the way a skeptical data scientist would:

- The coefficients are associations, and the team wasn't going to run experiments to confirm them.
- Splitting hours among causes needed an arbitrary allocation rule.
- Some inputs were confounded. "Few nurses have worked here" partly reflects whether a facility is a good place to work.

So I changed the model's job. **Expected fill** predicts how well a market's shifts should fill from their traits alone (pay vs local, posting time, approval, weekend, night, slots, license), deliberately leaving out nurse supply. Then:

```
actual fill  well below  expected fill  → the market can't fill shifts that should fill → Recruit / Improve reliability
expected fill well below the national mix → the shifts are hard to fill                 → Fix shifts
actual fill  well above  expected fill  → spare capacity                               → Account managers close leads
```

This claims less, but everything it claims can be checked. Every month you can compare expected with actual on new weeks and see whether it's still calibrated. Over 26 weeks it also gave the clearest executive insight: expected fill stayed flat while actual fill fell. The shifts didn't get harder to fill; the markets lost capacity.

I dropped two inputs on purpose. "Fewer than 10 facility reviews" was highly predictive, but it mostly measured how few nurses had been there, which is supply. Leaving it in would have explained away shortages at new facilities. Review scores, which facilities never see, went too.

## 7. Forecasting supply and demand

| Piece | Approach | What I learned |
|---|---|---|
| Demand | Straight-line trend over 26 weeks, projected 8 weeks ahead, with a band covering about 8 in 10 weeks; each market labelled steady, variable or volatile | Volatile markets go on a watch list instead of the recruiting list. It isn't worth investing in recruiting where demand swings |
| Supply, region level | Time-series forecast of weekly working nurses per region | Did **not** beat "same as last week". Too little history, and the trend reversed. Dropped |
| Supply, nurse level | Each recently active nurse's chance of working in the next 4 weeks (signals: shifts already booked, browsing last week, days since last shift), summed by region | Nearly unbiased while supply was falling. The naive forecast ran high. The scores also identify the nurses worth retention outreach |
| Supply inflow | Pipeline by market: sign-ups, approval rate, days to approve, first shift | In some short markets, approval took weeks. Speeding approvals up can beat buying more sign-ups |
| Organic returns | Share of lapsed nurses who return with no outreach, from a campaign's held-out control group | A bonus campaign pulled shifts forward but brought back no more nurses than its control group. Every win-back campaign now needs a holdout |
| Nurses short | Hours a week below expected fill ÷ weekly hours per nurse, as a low–high range, only in Recruit markets | New nurses work different hours from established ones, so a range is more honest than a single number |

## 8. Designing for each team, and for executives

Feedback came fast and specific, and most of it was about actionability:

- **"The bar of causes repeats, and the colours look the same."** Split into team views, each showing only what that team can act on.
- **"Callouts and cancellations are different problems."** One is nurse behaviour, the other facility behaviour, so they went to different owners.
- **"This chart is useless; the values are nearly identical."** Replaced with a repeat-callers chart, which concentrated where callouts come from.
- **"Clicking a row makes the page jump."** Replaced the panel below the table with an expandable row that keeps the scroll position.
- **"Nearby metros should be combined."** Added grouping by commuting region.
- **"What does 'passed over, reason unclear' even mean?"** Investigated it: much of it was misfiled callouts on multi-slot shifts and short timecards. Fixed the rules, and renamed what was left after what it actually is: weekend, night or multi-slot shifts.
- **"The people who manage facilities are client success, not account managers."** Every label now uses the team's real name.

For executives I researched how marketplaces present supply–demand balance and tried several layouts: bars by cause, a funnel, the company's existing flywheel diagram, and a Sankey. The flywheel showed only the losses the company was prioritizing at the time, and it implied a loop the data didn't support. The **Sankey** won: posted hours flow left to right, losses before booking peel up, losses after booking peel down, and each branch names its owning team. Every number and chart got a tooltip saying how it's calculated and what to do about it.

## 9. Making it cheap, fast and shared

The prototype queried the warehouse live on every page view. It was cheap per load, but it took about a minute, gave each viewer slightly different numbers, and needed warehouse access for every viewer. The data only changes daily, so I wrote the queries as dbt models rebuilt each morning, with a ticket for the data team. I then ported the dashboard into the company's internal tools platform: admin-only, read-only, calculations in pure functions with unit tests, and a demo fixture so it runs without credentials.

## 10. What the data couldn't answer yet

Paid ads wanted cost per working nurse by market. Auditing the data showed why that wasn't possible yet:
- install attribution had stopped syncing;
- ad spend by region was an even split, not real geography;
- most leads had no recorded channel.

I wrote that up as a data-team ticket rather than presenting a misleading number.

## 11. What I'd do differently

- **Start with the outcome breakdown.** The map was the wrong first artifact. A breakdown of where hours go would have changed the brief in the first week instead of the third.
- **Agree the official metric on day one.** Switching fill-rate definitions mid-project cost a rebuild.
- **Decide early how models will be used.** Asking "will anyone run an experiment on this?" before building the cause-split view would have gone straight to the benchmark.
- **Log actions from the start.** Without a record of which facilities were called or which campaigns ran, the tool can say where to act but not yet whether acting worked.
