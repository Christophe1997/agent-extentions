# Apply protocol

`/zettel-sync apply` turns the approved review doc into vault writes. It is
deliberately narrow: **it only ever creates files in `inbox/`.**

## Steps

1. **Locate the doc.** Default to the newest
   `_artifacts/zettel-sync/zettel-sync-*.md` — pick the latest date, and if that
   date has suffixed variants (`-2`, `-3`), the highest suffix. If the user
   named one, use that.
2. **Parse the `## Apply` section only.** For each item line that is checked
   (`- [x]`):
   - Read the target path from the backtick `` `inbox/<name>.md` ``.
   - Take the body from the **first ```markdown fenced block** after that line.
3. **Write each item:**
   ```
   obsidian_append_content("inbox/<name>.md", <body>)
   ```
   In mcp-obsidian, appending to a path that doesn't exist **creates** it. If
   `inbox/` doesn't exist yet, the first create makes it.
4. **Collision:** if `inbox/<name>.md` already exists (check via
   `obsidian_list_files_in_dir("inbox")` first), write to
   `inbox/<name>-vs<date>.md` instead — never overwrite.
5. **Ignore the `## Suggestions` section entirely.** Merges, orphan links, and
   reciprocal edits are the user's to perform during promotion.
6. **Update state.** In `_artifacts/zettel-sync/.state.json`:
   - applied concepts → `applied` (with date),
   - items that were unchecked → `declined` (so future runs skip them).
7. **Report** the exact list of files created, and remind the user that
   Suggestions are theirs to action.

## Safety assertions (enforce, don't assume)

- **inbox-only.** Before any write, assert the target path starts with
  `inbox/`. If a parsed path points anywhere else, **skip it and warn** — this
  is a corrupted doc, not an instruction to write into curated folders.
- **No deletes, ever.** This workflow has no delete path. A "merge" is a
  suggestion; the user deletes the folded note themselves.
- **No edits to `notes/` or `moc/`.** `obsidian_patch_content` is not used in
  apply mode.

## State file (`.state.json`)

Idempotency depends on a stable shape. Use:

```json
{
  "last_sync": "2026-05-28",
  "concepts": {
    "raft-consensus": { "status": "applied",  "date": "2026-05-28" },
    "b-tree-splits":  { "status": "declined", "date": "2026-05-28" },
    "io-uring":       { "status": "proposed", "date": "2026-05-28" }
  }
}
```

- `status` is one of `proposed` (in a review doc, not yet resolved), `applied`
  (written to `inbox/`), or `declined` (unchecked at apply time).
- Analyze adds `proposed` entries; apply flips them to `applied` / `declined`.
- Skip any concept already `applied` or `declined` when proposing (safety rule 5).

## First-run verification

The first time you apply against this user's vault, confirm the create mechanism
on a throwaway path **in the workflow's own scratch area** (not `inbox/`, so a
stray probe never pollutes the capture queue):
```
obsidian_append_content("_artifacts/zettel-sync/_probe.md", "<!-- zettel-sync probe, inert -->")
obsidian_get_file_contents("_artifacts/zettel-sync/_probe.md")   # confirm it exists
```
The probe is an inert HTML comment, so a leftover copy is harmless. If
`append_content` does **not** create missing files in this environment, fall
back to whatever create tool the server exposes (e.g. a `put`/`create` variant)
and note it for next time.
