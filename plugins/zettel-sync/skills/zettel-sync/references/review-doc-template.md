# Review document format

The review doc is written to `_artifacts/zettel-sync/zettel-sync-<YYYY-MM-DD>.md`.
It is the **contract** between analyze and apply: the user unchecks anything they
don't want, then `/zettel-sync apply` writes the still-checked **Apply** items.

Two top-level sections with different semantics:

- **## Apply** — items that `apply` will *create in `inbox/`*. Emitted
  **pre-checked (`- [x]`)** = pre-approved; the user unchecks to reject. `apply`
  writes the items still `- [x]`.
- **## Suggestions** — manual actions the user performs during inbox→notes
  promotion. **Never auto-applied.** Checkboxes here are just the user's own
  tracking, and stay `- [ ]`.

Apply-mode parsing depends on this structure, so keep it exact:
- Each applyable item is a single `- [x]` line (pre-checked) whose text contains
  a backtick path `` `inbox/<name>.md` ``. `apply` acts on the ones still `[x]`.
- The note body for that item is the **first fenced ```markdown block**
  following the item line. Apply extracts that block verbatim.

## Template

````markdown
---
generated_by: zettel-sync
created: 2026-05-28
days_scanned: 7
---
# Zettel sync — 2026-05-28

Scanned 7 days of sessions across N projects. Proposing **{X}** new seed notes,
**{Y}** MOC draft(s); flagging **{Z}** merge suggestion(s) and **{W}** orphan(s).

> **How to use:** uncheck anything you don't want, save, then run
> `/zettel-sync apply`. Only **Apply** items are written (all to `inbox/`).
> **Suggestions** are yours to action during promotion — nothing under them is
> ever written automatically.

---

## Apply — written to `inbox/` on approval

### New seed notes

- [x] Create `inbox/raft-consensus.md` — *Raft 共识算法*
  - **Why:** explored over 2 sessions; no existing note. **Evidence:** session 0cb3716e.
  - **Links proposed:** [[分布式锁]], [[Linux Internals MOC]]

```markdown
---
type: note
created: 2026-05-28
updated: 2026-05-28
tags: [distributed-systems, consensus]
---
# Raft 共识算法

> ...提要...

## 提纲(本次会话涉及)
- ...

## 相关
- [[分布式锁]]
```

### New MOC drafts

- [x] Create `inbox/Distributed Systems MOC.md` — *MOC for the `distributed-systems` cluster (6 notes)*
  - **Why:** 6 notes share `distributed-systems`, no MOC covers it.

```markdown
---
type: moc
created: 2026-05-28
updated: 2026-05-28
tags: [distributed-systems]
---
# Distributed Systems MOC

> ...
```

---

## Suggestions — manual, during promotion (not auto-applied)

### Near-duplicate merges

- [ ] Merge `http2-draft` → `http2` (similarity 0.62)
  - **Why:** same title, `http2-draft` is an empty stub. Fold and delete the stub.

### Orphan connections

- [ ] Link `namespace-and-cgroup` from somewhere
  - **Suggestion:** add `[[namespace-and-cgroup]]` under *Process & isolation* in
    [[Linux Internals MOC]] (it's already referenced there — verify), or from a
    new container note.

---
*State tracked in `_artifacts/zettel-sync/.state.json`.*
````

## Sizing

Respect the cap: at most ~6 new seed notes per run, ranked by evidence strength.
If more concepts qualify, list the overflow as a short bullet list under a
`### Deferred (next run)` heading — no embedded content, no checkbox — so the
user knows what was held back.
