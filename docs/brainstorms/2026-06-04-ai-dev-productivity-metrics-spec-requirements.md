---
date: 2026-06-04
topic: ai-dev-productivity-metrics-spec
---

# AI-Assisted Dev Productivity Measurement Spec (DORA + Collaboration Quality)

A **definition-first, tool-agnostic measurement framework**. It specifies *what* to
measure and *how to compute it* precisely enough that any tool (a Claude Code plugin, a
forge bot, a data pipeline) can implement it and produce comparable numbers. It does not
prescribe storage, dashboards, or a specific forge.

## Problem Frame
Teams are adopting AI-assisted development but lack a rigorous, shared way to assess
whether it improves real outcomes. Vendor "lines accepted" metrics measure activity, not
value, and are easy to game. DORA measures delivery outcomes but says nothing about the
*quality of the human-AI loop* that produces those outcomes. This spec links the two:
**Collaboration Quality** (how cleanly AI-assisted changes get accepted) as *leading*
indicators that should predict *lagging* DORA delivery outcomes — segmented by whether AI
was involved, so teams can answer "is AI actually helping, and where?"

## Core Decisions (resolved in brainstorm)
- **Artifact**: measurement spec, not a product or a plugin (tool-agnostic).
- **Unit of measurement**: the **pull request / merged change**. CQ and DORA share this grain so they join cleanly.
- **Combination model**: **leading → lagging linkage**. Two distinct metric families plus stated, testable hypotheses connecting them. No blended single score.
- **AI attribution**: a **cohort flag** per PR (`ai_assisted: true|false`). Source is pluggable (commit trailer, PR label, or tool telemetry) but **normalized into one field, with the originating `flag_source` recorded** so cross-team comparability is preserved.
- **Unreviewed merges**: PRs merged with no `review_requested` go in a **separate `unreviewed` bucket** — excluded from FPAR/Rework denominators, tracked as their own review-bypass metric.
- **Rework boundary**: **post-first-review churn (pre-merge)**. The "first pass" snapshot is the PR at its first `review_requested` event. Post-merge defects are owned by DORA only — never counted as rework (prevents double-counting across the linkage).

## Metric Definitions

### Family A — Collaboration Quality (leading, PR-grained)
- **R1. First-Pass Acceptance Rate (FPAR).**
  `FPAR = (reviewed merged PRs with no post-first-review code churn) / (reviewed merged PRs)`,
  over a window, computed per AI cohort. "First-pass" reference = PR head at first `review_requested`. The sole signal is post-first-review churn (consistent with the rework boundary) — a change-request resolved without code edits still counts as first-pass, since the code shipped as first submitted. Unreviewed PRs are excluded (see R2b).
- **R2. Rework Rate.** Two complementary forms, both defined on post-first-review / pre-merge activity:
  - *Population form*: `share of reviewed merged PRs that received ≥1 post-first-review change-set`.
  - *Intensity form*: `(lines added+deleted in commits after first review request, before merge) / (total lines changed in PR)`.
  Report both; the population form answers "how often," the intensity form answers "how much."
  Over reviewed merged PRs, **FPAR (R1) and the Rework population form are exact complements** (`FPAR + Rework_population = 1`) — both partition the same population on the same signal (presence of post-first-review churn).
- **R2b. Unreviewed-Merge Rate.** `(merged PRs with no review_requested) / (merged PRs)`, per cohort. Surfaces review-bypass; keeps FPAR/Rework honest about *reviewed* collaboration rather than inflating them.

### Family B — Delivery (lagging, DORA)
- **R3. Deployment Frequency** — deploys to production per unit time.
- **R4. Lead Time for Changes** — time from first commit (or PR open) to production deploy.
- **R5. Change Failure Rate** — share of deploys causing a degradation requiring remediation.
- **R6. Failed-Deployment Recovery Time** — time to restore service after a failed change.

### Linkage layer (the "combine")
- **R7. Stated leading→lagging hypotheses**, each expressed as a testable correlation an implementing tool *may* validate (not assert as fact):
  - H1: higher FPAR → lower Lead Time for Changes (less review ping-pong).
  - H2: higher Rework Rate → higher Change Failure Rate (churned code is defect-prone).
  - H3: AI-assisted cohort differs from non-AI cohort on FPAR/Rework, and that difference propagates to DORA.
- **R8. Cohort comparison** — every metric is reportable sliced by `ai_assisted` flag so AI's marginal effect is visible.

### Required signals (the contract every implementer must emit)
- **R9.** A normalized event set the spec depends on: `pr_opened`, `review_requested` (the first-pass boundary), `review_submitted{state}`, `commit{sha, timestamp, additions, deletions}`, `pr_merged`, plus deploy and incident events for DORA, and `ai_assisted{value, flag_source}` per PR (source recorded for comparability). The spec defines this minimal event schema; collection sources are pluggable.

## Success Criteria
- Every metric has an unambiguous formula, named signal source, and defined edge-case handling — no "interpretation needed."
- **Interoperability**: two independent implementations run on the same repo history produce identical metric values, given the same required-signal inputs (the spec leaves no computational ambiguity). Defining an acceptable tolerance for *differing* signal sources is deferred to planning.
- The `ai_assisted` cohort comparison is computable from the required signals alone.
- Each linkage hypothesis (R7) is stated as something a tool *could* statistically test, with the join key (PR id) specified.
- A reader can implement the spec without contacting the authors.

## Scope Boundaries
- **Not individual-developer surveillance/ranking.** Metrics aggregate at team/cohort level only; per-person leaderboards are an explicit non-goal.
- **No composite "productivity score."** The two families stay distinct.
- **No collection tooling, storage, schema-beyond-events, or dashboard design.** Spec only.
- **No mandated forge or AI vendor.** Signal sources are pluggable behind the R9 event contract.
- **Post-merge defects are DORA-only**, never rework — to keep the leading/lagging linkage clean.
- Pre-first-review churn (author still drafting) is explicitly *not* rework.

## Dependencies / Assumptions
- A forge emits (or can be derived to emit) PR lifecycle + review events with timestamps.
- Deploy and incident signals exist for DORA (may be a separate system).
- An `ai_assisted` flag can be attached to a PR by at least one source (commit trailer, label, or telemetry), normalized per R9.
- Squash/rebase merges may collapse commit granularity — affects R2 intensity form.

## Outstanding Questions

### Deferred to Planning
- [Affects R3-R6][Needs research] Adopt DORA's standard definitions verbatim vs. tailor thresholds (e.g. what severity counts as a "failure") for the AI-assisted context.
- [Affects R2][Technical] How to handle **squash/force-push** that erases post-first-review commit granularity for the intensity form — fall back to population form, or reconstruct from review-thread diffs.
- [Affects R8][Technical] Default **aggregation window** and minimum sample size before cohort comparisons are reported as meaningful.
- [Affects R9][Needs research] Whether bot/dependabot/auto-generated PRs are excluded by default and how they're detected.

## Next Steps
→ `/ce:plan` for structured implementation planning. No blocking questions remain.
