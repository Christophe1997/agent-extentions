# Comparison & Merge

How to turn N candidate reports into one merged result.

## 1. Build the head-to-head table

Normalize every candidate's report into one table so differences are visible at a
glance. One row per dimension, one column per candidate:

| Dimension | Candidate A (`<lens>`) | Candidate B (`<lens>`) | Candidate C (`<lens>`) |
|-----------|------------------------|------------------------|------------------------|
| Acceptance bar (tests/build/lint) | pass / skip / fail + detail | … | … |
| Lens goal achieved | … | … | … |
| Simplicity (LOC, files touched) | diffstat | … | … |
| Correctness / edge cases | … | … | … |
| Risk / blast radius | … | … | … |
| Standout idea | the one thing it did best | … | … |

Drop or rename dimensions to fit the task. Always include the acceptance bar and
"standout idea" — the latter feeds the graft step.

## 2. Score and pick the winner

**Gate first.** Acceptance bar and lens goal are gates: any candidate that fails
either — or is incomplete — is disqualified before scoring.

**Score the survivors (weighted blend).** Score each surviving candidate on the
four criteria below, then pick the highest weighted total. The criteria follow
**Lazy Industriously**, **Impatient Patiently**, **Proud Humbly**; reuse and
modularity carry the most weight.

| Criterion | Good signal | Weight |
|-----------|-------------|--------|
| **DRY / reuse** | Uses a third-party library suited to the goal, or abstracts a shared lib/util used across modules | ×3 |
| **Modularity** | Correctly splits and couples interfaces; no domain leak — domain/business logic stays inside its boundary and never bleeds into adjacent layers (transport, persistence, UI) | ×3 |
| **Project convention** | Follows the codebase's coding taste, library preferences, and existing patterns | ×2 |
| **Correctness depth** | Considers more edge cases (beyond the gate's basic bar) | ×2 |

Score each criterion (e.g. 0-3); the highest weighted sum wins. Retune weights per
task — a hot path may raise correctness depth; a throwaway may drop convention.

**Near-tie.** If the top two land within ~1 weighted point, break the tie toward
(a) the smaller diff / lower blast radius, then (b) the candidate whose standout
ideas graft most cleanly onto the others.

**No candidate clears the gate.** Adopt the candidate closest to passing as the
base and fix it forward until the acceptance bar passes, then continue to the
merge. State plainly in the final report that the base started below the bar and
what had to be fixed.

After applying the rubric, present the table + your recommended winner + one-line
rationale, then confirm the pick with the user via `AskUserQuestion` before
merging. The user may override the recommendation.

## 3. Merge — winner-base + graft

Use the per-candidate bookkeeping recorded at launch (lens → worktree path,
branch, HEAD SHA). **Graft before cleanup** — worktrees share one object store, so
a candidate's commits stay cherry-pickable by SHA only while a ref keeps them
alive; removing a worktree/branch first can strand them.

1. **Adopt the winner as the base.** Cherry-pick the winner's commits by SHA (or
   merge its recorded branch) into the main working tree. Verify the acceptance bar
   still passes after landing.
2. **Graft the standout ideas.** From each runner-up's "standout idea" row, pull
   the specific superior pieces (a tighter helper, a missing test, a cleaner
   interface) into the base — cherry-picking the relevant commit or hand-applying
   the snippet. Graft discrete, reviewable changes — not whole files. Re-verify
   after each graft.
3. **Clean up.** Remove the loser worktrees by their recorded path
   (`git worktree remove <path>`; unchanged ones auto-remove). Confirm
   `git worktree list` shows only the main checkout.

Report the final state: what was adopted as base, what was grafted from whom, and
the acceptance status of the merged result.
