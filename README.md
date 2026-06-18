# Requirements

Replace the CUO's manual work with AI agent. Which will digest the data, and and produces both an interactive dashboard
and an executive narrative — automatically.

# Input

- 4 csv files

## Data Understanding

I'm not an insurance person, so before writing any code I worked through
what each file actually represents in plain terms.

**The big picture:** it's like a sales CRM pipeline, but for insurance.
Every week, for each of 8 business lines, four things get tracked: 

Did we get asked to quote business, and what happened to it? (submissions file)

How much money did we actually collect vs. what we expected? (premium file)

What deals are still "in progress," not yet decided? (pipeline file)

How many claims came in, and how much are they costing us? (loss file)

All four files join on the same two columns:
`week_ending` + `lob` (line of business) — no other keys needed.

### `case4_weekly_submissions.csv` — what happened to each deal

Every new risk a broker brings us ends up in exactly one bucket:

| Column | Meaning |
|---|---|
| `week_ending` | The Sunday closing that week |
| `lob` | Business line (Cyber, Environmental, etc.) |
| `submissions_count` | New deals that came in this week |
| `quoted_count` | We gave a price, still pending the customer's decision |
| `bound_count` | Became an actual signed policy (a win) |
| `declined_count` | We said no outright |
| `ntu_count` | "Not Taken Up" — we quoted, customer went elsewhere (lost the bid, not our refusal) |

**Hit rate** = `bound / (bound + quoted + declined + ntu)` — a conversion
rate, same idea as a sales funnel win %.

### `case4_weekly_premium.csv` — the money

| Column | Meaning |
|---|---|
| `actual_gwp` | Actual premium revenue booked this week for this line ("GWP" = Gross Written Premium) |
| `plan_gwp` | Budgeted/target revenue for this week |
| `ytd_actual` / `ytd_plan` | Running totals of the above since the start of the year |

The whole story here is just actual vs. plan — same as "are we ahead or
behind our quarterly sales target."

### `case4_pipeline.csv` — deals still in limbo

| Column | Meaning |
|---|---|
| `open_quotes_count` | Quotes currently pending a customer decision |
| `open_quotes_gwp_est` | Estimated £ value of those pending quotes if they all closed |
| `avg_days_in_pipeline` | Average time those open quotes have been stuck unresolved |

**Note:** I checked this file closely for a hidden signal and it's
mostly noise — no clean trend for any business line across the 12
weeks. Worth knowing that's a deliberate finding, not a gap in my
analysis.

### `case4_loss_indicators.csv` — what claims are costing us

| Column | Meaning |
|---|---|
| `new_claims_count` | New claims reported this week |
| `new_claims_incurred_est` | Estimated £ cost of those new claims |
| `attritional_loss_ratio_ytd` | Cumulative (claims paid ÷ premium collected) since the start of the year, as a fraction (e.g. `0.554` = 55.4%) |

**Loss ratio** is the headline profitability metric: under ~60% is
healthy, climbing past it means the line is paying out more in claims
relative to premium than it should. Important quirk: this column is
already a running year-to-date figure, not a "this week only" number —
week 12 already has weeks 1–11 baked in, so it plots as a smooth trend
without needing my own rolling calculation. "Attritional" just means
ordinary, expected claims (as opposed to one catastrophic loss) — not
relevant to how I use the column.

# Output

- Sample executive narrative output
- Dashboard
- Prompt file(s)

# Thoughts

## 1. build the project structure

built as in Implementation

## 2. Signal detector

I have 4 confirmed signals, each needing a rule that requires a sustained pattern — never trigger off a single week. The detector lives in `detect.py`, completely separate from the LLM. Ranking is deterministic in code; the LLM only writes the narrative from results I've already decided.

Each signal is one function returning a dict (lob, type, title, detail, action) or None. A `detect_all()` wrapper calls all four and returns the non-None results. All thresholds live in `config.py` so they can be tuned without touching logic.

- **Signal 1 — Excess Casualty:** actual GWP(revenue) below 60% of plan in at least 9 of 12 weeks — structural, not a blip. → premium file only
- **Signal 2 — Cyber hit rate:** average hit rate weeks 1–8 vs weeks 9–12 drops by more than 10pp — sustained collapse, not a one-off. submissions file only
- **Signal 3 — Environmental loss ratio:** latest YTD loss ratio exceeds week-1 value by more than 10pp *and* is above the 60% target — direction matters as much as level. → loss file only
- **Signal 4 — Political Violence:** GWP beats plan in at least 8 of 12 weeks *and* loss ratio stays below 60% — growth is only an opportunity if it's profitable. → premium and loss files combined

## 3. Prompt files
There will be some placeholders in the prompt files. I need code to replace them with the actual data.

## 4. Agent orchestrator
Wire the data loading, detectors running, generating the prompt, calls LLM, writing the analysis.json and narrative.txt files.

## 5. Dashboard
A JSON file with the following structure:
```json
  {
    "narrative": "...",
    "signals": [...],
    "charts": {
      "gwp": {                                                                      
        "weeks": ["Jul 07", "Jul 14", ...],
        "lobs": {
          "Cyber": { "actual": [...], "plan": [...] },
          ...
        }
      },
      "hit_rate": {
        "weeks": [...],
        "lobs": {
          "Cyber": [0.27, 0.35, ...],
          ...
        }
      }
    }
  }

```

A self-contained HTML file.

# Implementations
See this in jupyter notebook