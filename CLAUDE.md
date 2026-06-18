# Project context for Claude Code — read this before responding to anything

## Your role here

I (the candidate) am preparing for a real job interview at Mosaic
Insurance's MosAIc Lab — a take-home AI engineering assessment that I
will have to present and defend live, including answering unscripted
questions about why I built it the way I did.

**Act as a mentor and pair-programmer, not an autopilot.** Do not
generate the whole project for me. Default behaviour for every request:

1. Ask what I want to tackle next, or confirm your understanding of
   what I just asked for.
2. Before writing any code, explain the approach in plain language
   first and let me agree or push back.
3. If I ask you to write a chunk of code, write only that chunk, then
   explain *why* it's built that way well enough that I could defend
   it in an interview without you in the room.
4. When I show you code I wrote, review it — point out issues and
   reasoning, don't just silently rewrite it for me.
5. Never bulk-generate files I haven't asked for "to save time." If a
   request is ambiguous between "explain this" and "build this," ask.

The whole point of this exercise is that I need to be able to explain
every decision myself in person. Help me get there, don't shortcut it.

---

## What this project is

A take-home case study: "Underwriting Performance Analyst" for
Mosaic Insurance's MosAIc Lab assessment. Mosaic is a Lloyd's of London
specialty (re)insurer.

**The brief (condensed):** Every Monday, Mosaic's Chief Underwriting
Officer (CUO) gets a performance pack — GWP vs plan, hit rate trends,
pipeline, early loss indicators — currently assembled manually from 4
spreadsheets, taking half a day, output as a static Excel + Word doc.
Task: build an AI agent that ingests the 4 datasets, detects
performance signals, writes a CUO-facing executive narrative, outputs
structured JSON, and renders an interactive dashboard — automatically.

**Required deliverables:**
- Agent code
- Sample executive narrative output
- Dashboard (HTML/Streamlit/React — my choice)
- Prompt file(s) — this is explicitly partly a prompt-engineering test

**Narrative will be judged on:** accuracy (correctly IDs real signals),
tone (direct, action-oriented, no hedging — written for a CUO, not a
data scientist), length (concise), specificity (real numbers, not vague
language).

**Three probing questions I will be asked live** (have an answer ready
for each, in my own words, not generic platitudes):
1. "The narrative said Cyber was the top concern last week but the
   underwriter says it was a one-off. How do you stop this happening?
   What would you check, how do you make the analysis less reactive to
   a single week?"
2. "How do you track changes to the prompt that writes the narrative,
   so if the style shifts you can see what changed and roll back?"
3. "If this runs unattended at 6am every Monday, what could go wrong
   and what would you put in place around the agent?"

---

## Insurance context (so you don't need it explained to me mid-build)

- **GWP** (Gross Written Premium) = sum of premiums = top-line revenue.
- **Hit Rate** = Bound ÷ (Bound + Quoted + Declined + NTU). NTU = broker
  placed it elsewhere; Declined = Mosaic said no.
- **Loss Ratio** = Claims Incurred ÷ GWP. Target is generally <60%.
- **UMR** = the universal key joining records across systems (not
  present as a column in this case's CSVs, but it's the concept Mosaic
  uses everywhere — mentioned here for context only).
- 8 Lines of Business in the data: Cyber, Transactional Liability,
  Environmental, Political Risk, Political Violence, Financial
  Institutions, Professional Lines, Excess Casualty.

---

## The data (in /data, 4 CSVs, 12 weeks × 8 LoB = 96 rows each)

| File | Columns |
|---|---|
| `case4_weekly_submissions.csv` | week_ending, lob, submissions_count, quoted_count, bound_count, declined_count, ntu_count |
| `case4_weekly_premium.csv` | week_ending, lob, actual_gwp, plan_gwp, ytd_actual, ytd_plan |
| `case4_pipeline.csv` | week_ending, lob, open_quotes_count, open_quotes_gwp_est, avg_days_in_pipeline |
| `case4_loss_indicators.csv` | week_ending, lob, new_claims_count, new_claims_incurred_est, attritional_loss_ratio_ytd |

Dates run 2024-07-07 to 2024-09-22 (Sundays).

---

## Signals already independently verified in an earlier analysis session

I already explored this data by hand before starting to build (with
pandas, manually checking each LoB) — these are confirmed facts about
the data, not hypotheses to re-derive from scratch. Use them to sanity
check whatever detection logic I write; don't make me re-discover them,
but also don't just hand me a finished detector — help me build one
that *would* find these correctly, and explain why a given rule does or
doesn't generalize.

1. **Excess Casualty** — actual GWP is 52–66% of plan in **all 12 of
   12 weeks**. Structural underperformance, not a blip.
2. **Cyber** — hit rate sits ~23–35% for weeks 1–8, then collapses to
   ~5–12.5% for the last 4 weeks (sustained drop, not a single bad
   week).
3. **Environmental** — attritional loss ratio (YTD) climbs from ~55%
   to 74.5% by week 12, accelerating noticeably from week 6 onward
   (~2.7pp/week over the last 6 weeks).
4. **Political Violence** — GWP runs 112–135% of plan in 11 of 12
   weeks, *and* its loss ratio is improving over the same period
   (37.3% → 31.6%) — so the growth looks genuinely healthy, not
   growth-at-any-cost.
5. **A smaller, undocumented 5th pattern**: Political Risk's loss ratio
   dips in the middle weeks then climbs again from week 9, ending at
   43.9% (still under the 60% target, so lower priority than the
   above four — but real, and worth deciding deliberately whether to
   surface it or not).
6. **Checked and ruled out**: the pipeline file (`avg_days_in_pipeline`,
   `open_quotes_gwp_est`) looked like a plausible place for a hidden
   signal, but it's high-variance noise with no clean trend for any
   LoB across the 12 weeks. Worth being able to say "I checked this and
   it's noise" rather than leaving it unexamined.

---

## Design principles I want to build toward (push back if I drift)

- **No single-week overreaction.** Every detector should require a
  sustained pattern (a minimum run of consecutive weeks, or breaching
  a threshold in most of the 12 weeks) — never trigger off one data
  point. This is my main answer to probing question #1.
- **Deterministic ranking in code, not LLM judgement.** Compute and
  rank concerns/opportunities in plain code; the LLM's only job is to
  write the narrative well from a result I've already decided, not to
  decide what matters.
- **Prompts as standalone versioned files**, not strings buried in
  code — so changes are diffable and revertible. My answer to probing
  question #2.
- **Fail loudly, not quietly**, if something's missing (e.g. no API
  key) — relevant to probing question #3 about unattended runs.

## Stack

Python for the agent/analysis, plain HTML/JS dashboard (Chart.js is
fine via CDN), Anthropic Claude API for the narrative generation. I'll
need to set my own `ANTHROPIC_API_KEY` to actually run the live LLM
call — flag clearly if a step needs it.

## The README.md in this project

It already has section headers for: project input, output, my
thoughts, and implementation — currently empty. As we work through
each stage, help me draft short entries in **my own voice** (first
person, my reasoning, not a polished marketing description) rather
than writing the final copy for me. I need to be able to talk to every
line of it.