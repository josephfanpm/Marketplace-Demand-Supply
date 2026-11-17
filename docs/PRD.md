# PRD: Market Map

**Owner:** Joseph Fan, Product · **Status:** Internal tool live; port to internal tools platform in review · **Audience:** Leadership, Recruiting & Marketing, Client Success, Nurse Operations, Sales

No company figures appear in this document.

## 1. Problem

Fill rate is falling while demand grows, and the organisation's default response is to recruit more nurses. But posted hours are lost for many reasons, and only some are a supply shortage. Without knowing why each hour is lost and who can fix it, teams spend effort and budget on problems their tools can't solve.

## 2. Goals

1. Show each team the share of lost hours it owns, and the markets and facilities where acting matters most.
2. Separate "the market can't fill shifts that should fill" (a supply or reliability problem) from "the shifts are hard to fill" (a shift problem).
3. Give leadership one page showing whether supply is keeping up with demand.
4. Use the company's official fill-rate definition everywhere.

## 3. Non-goals

- Person-level predictions (callout risk, churn risk) on this tool. They belong in operations tools.
- Attributing lost hours to individual causes with model coefficients.
- Real-time data. Daily refresh is enough.
- Writing anything back to production systems.

## 4. Users and jobs to be done

| User | Job | Primary view |
|---|---|---|
| Leadership | Know whether supply keeps up with demand, and where it doesn't | Overview |
| Recruiting, Marketing, Paid ads | Decide where and for which license to recruit, and whether to win back lapsed nurses first | Recruiting |
| Sales, Recruiting | Check new facilities are ramping up | New markets |
| Nurse operations | Reduce callouts and no-shows; refill faster | Nurse reliability |
| Client success | Get facilities to post earlier, use instant book, pay near the local rate, confirm applicants and give reasons for deletions | Facility practices |
| Sales / Account managers | Close leads where there's spare capacity | Overview (spare capacity list), Recruiting (statuses) |

## 5. Definitions

| Term | Definition |
|---|---|
| Fill rate | Hours worked ÷ slot-hours posted (official definition). Counts re-posted replacement slots and early deletions as posted |
| Expected fill | Predicted fill from shift traits only: pay vs the local median for license and state, posting lead time, weekend, time of day, slots, license, length, approval required, new facility. No nurse-supply inputs. Refit monthly |
| Fill vs expected | Fill rate minus expected fill, in points |
| Slot outcome | What happened to each posted slot: worked, nobody applied, applied but not booked, deleted (<24h or 24h+ before start), slots removed, called out, cancelled by facility, no-show, invalid timecard |
| Nurses short | Weekly hours below expected fill ÷ weekly hours per nurse, by license, as a low–high range; only for markets marked Recruit nurses |
| Market status | Recruit nurses (≥8 pts below expected, and more open slots than callouts); Improve nurse reliability (≥8 pts below, callouts dominate); Fix shifts (expected ≥4 pts below the national mix); Spare capacity (≥8 pts above expected); Healthy; Too little data (<40 posted hrs/wk) |

## 6. Requirements

### Overview (leadership)
- **R1** Headline tiles: fill rate, slot-hours posted per week, nurses working per week, and new nurses per week. Each is the last 4 full weeks, compared with six months earlier.
- **R2** Weekly fill rate vs expected fill over 25 weeks, on one percentage axis.
- **R3** A Sankey of posted hours, from original slots plus re-posted slots, through booked, to worked:
  - losses before booking peel up and losses after booking peel down;
  - each loss names its owner and links to that team's tab;
  - a table view is available.
- **R4** A state map in three categories (short of nurses, enough nurses, spare capacity), with nurses short printed on short states.
- **R5** Two lists: the biggest nurse gaps (license mix, fill vs expected, approval wait) and markets with spare capacity.

### Recruiting
- **R6** Ranked "where to recruit" list. Eligible markets are Recruit nurses, ≥3 nurses short, with steady or variable demand, 12+ weeks of history, and demand not shrinking more than 15%.
- **R7** Each row expands to a detail panel with:
  - nurses short (range);
  - posted hours and forecast;
  - fill vs expected;
  - a plan sentence matched to the market's status;
  - the pipeline (sign-ups, approvals, first shifts, days to approve);
  - links to the reliability and practices tabs with the state filter already set.
- **R8** A watch list for markets that are short but volatile, new or shrinking.
- **R9** Grouping by commuting region, a table of all metros with pagination, and copy as TSV.

### New markets, reliability, practices
- **R10** New markets: launch status (needs nurses / ramping well / no shifts yet) based on fill vs expected at new facilities.
- **R11** Reliability:
  - weekly lost hours to callouts and no-shows;
  - repeat callers (counts only, no names);
  - facilities hit hardest, filterable by state.
- **R12** Practices:
  - facility list of facility-side losses (late deletions, removed slots, cancellations, applicants not booked, invalid timecards);
  - the same list shows expected fill, share posted under 48h, share needing approval, pay vs local and deletes with a reason;
  - fill by posting lead time, by pay band, and instant book vs approval.

### Cross-cutting
- **R13** Every number and chart has a tooltip saying how it's calculated and what to do about it.
- **R14** Definitions show only the entries for the open tab.
- **R15** Admin-only and read-only; no person-level data shown.
- **R16** Data rebuilt daily; the data date is shown.

## 7. Acceptance criteria

1. **Flow:** the flow balances. Posted − losses before booking = booked, and booked − losses after booking = hours worked (within rounding).
2. **Nurses short:** it adds up the same across the summary, the overview and the state map.
3. **Expected fill:** on 4 held-out weeks, predicted and actual fill agree within a few points in every tenth of the predicted range.
4. **Statuses:** every market with ≥40 posted hours a week has exactly one status, and its detail panel shows a next step matching that status.
5. **Calculations:** derived values are unit-tested as pure functions.

## 8. Metrics

| Type | Metric |
|---|---|
| Outcome | Fill vs expected in Recruit markets (should close); expected fill in Fix shifts markets (should rise); callout refill rate; days to approval |
| Adoption | Weekly active viewers by team; actions logged against market status (future) |
| Model health | Calibration after each monthly refit |

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| People read expected fill as causal | Labelled a benchmark, never "hours lost to X"; the fitted and true effects in the demo show the difference |
| The model drifts as the marketplace changes | Monthly refit and calibration check, with coefficients versioned |
| State map hides short metros | Ranked lists sit next to the map |
| Official fill rate counts re-posts and early deletions | Explained in tooltips and drawn in the Sankey (grey for not-real misses) |
| Teams don't act | Owner names on every loss, links to the owning tab, a next-step sentence per market |

## 10. Open questions

- Who owns the monthly model refit once the data team takes over the daily tables?
- Which actions (facility calls, campaigns) can be logged so the tool can show whether acting worked?
- When install attribution and regional spend are fixed, should cost per working nurse by market sit on the Recruiting tab or in a separate paid-ads view?
