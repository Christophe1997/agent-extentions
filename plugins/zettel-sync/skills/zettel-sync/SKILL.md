---
name: zettel-sync
description: This skill should be used when the user asks to sync, update, or grow their Obsidian vault / Zettelkasten-style vault from recent Claude Code sessions — harvest explored concepts into draft notes, find orphan notes, detect near-duplicate notes, or propose a new MOC. Produces one batched-approval review document; a separate apply step writes the approved items.
argument-hint: "[--days N] [--dry-run] | apply"
allowed-tools: [Bash, Read, Write, Task]
---

# zettel-sync

Maintain a structured Obsidian vault (Zettelkasten-style) from recent Claude Code sessions. One run
analyzes your sessions and your vault, then writes a **single batched-approval
review document**. Edit it (uncheck anything you don't want), then run
`/zettel-sync apply` to write the still-checked items.

**Requires** a running Obsidian with the Local REST API plugin. This plugin
**bundles its own Obsidian MCP server** (`.mcp.json`, via `uvx mcp-obsidian`),
so setup is just exporting `OBSIDIAN_API_KEY` (from the Local REST API plugin's
settings). The bundled server's tools are namespaced
`mcp__plugin_zettel-sync_obsidian__obsidian_*`; a globally-configured server
instead appears as `mcp__obsidian__obsidian_*`. Use whichever is available
(prose below uses the bare `obsidian_*` action names). If
`obsidian_list_files_in_vault` fails on both, tell the user the server isn't
reachable — check Obsidian is open and `OBSIDIAN_API_KEY` is set — and stop.

## Modes

| Invocation | What it does |
|------------|--------------|
| `/zettel-sync` | Analyze sessions + vault, write the review doc. **No vault writes** except the review doc. |
| `/zettel-sync --days N` | Same, scanning the last N days (default 7). |
| `/zettel-sync --dry-run` | Analyze and print the proposals to chat; do **not** write the review doc. |
| `/zettel-sync apply` | Read the latest review doc and write all still-checked items. |

## Non-negotiable safety rules

These come from the vault's own philosophy (curation over accumulation) and the
user's explicit instruction. Violating them is a defect, not a judgment call.

1. **inbox-first.** Every note this workflow *creates* — new seed notes and MOC
   drafts alike — goes to `inbox/`, never directly to `notes/` or `moc/`. The
   inbox→notes promotion is the user's manual step.
2. **Never modify or delete existing curated notes.** Near-duplicate merges,
   orphan reconnections, and reciprocal links are **suggestions in the review
   doc only** — the user applies them by hand during promotion.
3. **Match the vault's language.** Draft note prose in the same language the
   existing notes use — infer it from the representative notes read in Step 0;
   never assume a language. Tags stay lowercase-English kebab-case; code and
   technical terms keep their original form.
4. **Conservative and ranked.** Cap new-note proposals at ~6 per run, ranked by
   evidence strength. A flood betrays the vault's philosophy.
5. **Idempotent.** Never re-propose a concept whose `.state.json` `concepts`
   entry has `status` `applied` or `declined`.

See `references/drafting-convention.md`, `references/review-doc-template.md`,
and `references/apply-protocol.md` for the details each phase needs.

---

## Analyze mode (default)

### 0. Load the vault convention (do not hardcode it)
- `obsidian_get_file_contents("_templates/_schema.md")` → the authoritative
  frontmatter contract. Re-read it every run; the user may have evolved it.
  **If `_schema.md` is absent**, infer the contract from 2–3 representative
  `notes/` and say so in the review doc.
- `obsidian_list_files_in_dir("notes")` and `("moc")` → current note/MOC stems.
- `obsidian_get_file_contents` on 1–2 representative notes (e.g. a long one) to
  re-learn the note shape (frontmatter → `# Title` → `> 提要` → sections).

### 1. Harvest concepts from sessions
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/harvest_concepts.py" \
  --days "${DAYS:-7}" --format text --output /tmp/zettel-sync/digest.txt
```
- With `--output`, the script writes a summary line to **stderr**:
  `wrote <N> sessions, <chars> chars -> ...`. Read `<chars>` from there (the
  digest itself is in the file). The total-size cap is 120000 chars.
- **If `<chars>` is large** (say > 90000, i.e. nearing the 120000 cap), fan out:
  launch one `general-purpose` Task agent per project, each given that project's
  slice of the digest, asked to return JSON
  `[{concept, domain, evidence, session_id}]`. Merge the results.
- **Otherwise** read `digest.txt` yourself and extract the same structure.
- Keep only **substantive technical concepts** (distributed systems, Go
  internals, algorithms, kernel, networking, etc.). Drop tooling chatter,
  meta-discussion, and one-off trivia. Rank by how deeply each was explored.

### 2. Match against the vault
For each candidate concept:
- `obsidian_simple_search(concept)` and a search on 1–2 key terms.
- Compare hits against the `notes/` stem list.
- Classify **covered** (a note already exists) vs **missing**.
- Drop any concept whose `.state.json` `concepts` entry has `status` `applied`
  or `declined`.

### 3. Run structural analysis (scans the vault on disk — no snapshot to build)
The vault is local, so `vault_graph.py` reads it straight off disk. **Do not**
`batch_get` note bodies into the conversation or hand-write a snapshot — that
routes the whole vault through the model. Just run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault_graph.py" --format json
```
- It resolves the vault root from `--vault-path`, then `$OBSIDIAN_VAULT_PATH`,
  then Obsidian's `obsidian.json` (the open vault). The Local REST API does
  **not** expose the absolute root, which is why the script reads `obsidian.json`
  itself. If it can't decide (multiple open vaults, non-standard config) it exits
  with guidance — re-run with `--vault-path /abs/path`, asking the user for their
  vault's absolute path if it's not already known.
- By default it scans `notes/` and `moc/` (override with `--dirs a,b`). It
  returns `orphans`, `moc_gaps` (tags with ≥5 notes and no MOC), and
  `near_dup_pairs`. The script narrows; **judge** which candidates are real.
- **Offline / sandboxed fallback only:** if this session genuinely can't read the
  vault directory, build a snapshot tree with `obsidian_batch_get_file_contents`
  under `/tmp/zettel-sync/snapshot/<relpath>` (frontmatter intact) and run with
  `--snapshot /tmp/zettel-sync/snapshot` instead.

### 4. Draft proposals
Per `references/drafting-convention.md`, conservative and ranked:
- **New seed notes** (`inbox/`) for missing concepts — in the vault's language, frontmatter from
  the schema, `# Title`, `> 提要` thesis, an outline of the sub-points the
  session actually covered, and proposed `[[links]]` to related existing notes.
- **New MOC drafts** (`inbox/`, as a draft) for each real `moc_gaps` cluster.
- **Merge suggestions** for `near_dup_pairs` you confirm — report only.
- **Orphan connections** — for each orphan, suggest which existing note/MOC
  should link to it — report only.

### 5. Write the review document
Write the review doc to `_artifacts/zettel-sync/zettel-sync-<YYYY-MM-DD>.md`
following `references/review-doc-template.md`. **Apply** items are emitted
**pre-checked (`- [x]`)** — they are pre-approved; the user *unchecks* anything
to reject it. **Suggestions** (merges, orphan links — manual promotion) stay
`- [ ]`. Embed each proposed note's full content and each suggestion's
rationale + evidence.

Avoid clobbering: first `obsidian_list_files_in_dir("_artifacts/zettel-sync")`.
If today's doc already exists, write `zettel-sync-<date>-2.md` (next free
suffix) rather than appending — appending a second review onto the first breaks
apply-mode parsing. Then tell the user the path and that they uncheck items
before `/zettel-sync apply`.

Update `_artifacts/zettel-sync/.state.json` with `last_sync` and the proposed
concepts (status `proposed`). **In `--dry-run`, print proposals to chat and
write neither the doc nor `.state.json`.**

---

## Apply mode (`/zettel-sync apply`)

Follow `references/apply-protocol.md`. In short:
1. Read the latest `_artifacts/zettel-sync/zettel-sync-*.md` (or a named one).
2. Parse the **Apply** section; collect items still checked (`- [x]`).
3. For each, `obsidian_append_content("inbox/<name>.md", <content>)` to create
   the seed note / MOC draft. **Only `inbox/` is ever written.**
4. **Suggestions** items are never auto-applied — they are the user's to do.
5. Update `.state.json`: move applied concepts to `applied`, unchecked ones to
   `declined`. Report exactly what was written.

Never delete, never touch `notes/` or `moc/`. If an `inbox/<name>.md` already
exists, append a `-<date>` suffix rather than overwrite.
