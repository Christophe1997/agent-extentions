#!/usr/bin/env python3
"""Structural analysis of an Obsidian vault snapshot.

Pure graph/text math that the model should NOT do by hand: it narrows a whole
vault down to three small candidate lists the model can then judge.

  orphans        atomic notes (type: note) with zero incoming [[links]]
  moc_gaps       tags shared by >= N notes with no MOC covering them
  near_dup_pairs note pairs whose similarity() score clears a threshold

Input: by default it scans your live Obsidian vault on disk directly, resolving
the vault root from --vault-path, $OBSIDIAN_VAULT_PATH, or Obsidian's
obsidian.json. The vault is local, so there is no MCP round-trip and no note
content is copied through the model. --snapshot DIR remains as an offline
fallback over a prebuilt tree of .md files.

Usage:
  python3 vault_graph.py [--vault-path DIR] [--dirs notes,moc]
                         [--moc-threshold N] [--dup-threshold F]
                         [--format json|text]
  python3 vault_graph.py --snapshot DIR     # offline: analyze a prebuilt tree
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from dataclasses import dataclass, field

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
WORD_RE = re.compile(r"\w+", re.UNICODE)

# Types that are entry points / scaffolds, not atomic notes.
NON_ATOMIC = {"moc", "hub", "template"}


@dataclass
class Note:
    path: str          # relative path within the snapshot
    stem: str          # filename without .md — how wikilinks address it
    type: str          # frontmatter `type`, or "" if absent
    title: str
    tags: list[str]
    body: str
    links: set[str] = field(default_factory=set)  # outgoing link targets (stems)


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Minimal YAML — enough for this vault's
    schema (type / tags), no external dependency."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    fm: dict = {}
    key = None
    block_list: list[str] = []
    for line in raw.splitlines():
        if key == "tags" and line.lstrip().startswith("- "):
            block_list.append(line.lstrip()[2:].strip())
            continue
        if key == "tags" and block_list:
            fm["tags"] = block_list
            key, block_list = None, []
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "tags":
            if val.startswith("[") and val.endswith("]"):
                fm["tags"] = [t.strip() for t in val[1:-1].split(",") if t.strip()]
                key = None
            elif val:
                fm[key] = [val]
                key = None
            else:
                block_list = []  # expect a block list on following lines
        else:
            fm[key] = val
    if key == "tags" and block_list:
        fm["tags"] = block_list
    return fm, body


def link_target(raw: str) -> str:
    """Normalize a wikilink interior to a note stem: drop #heading and |alias."""
    return raw.split("|")[0].split("#")[0].strip()


def load_note(path: str, rel: str) -> Note:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_frontmatter(text)
    stem = os.path.splitext(os.path.basename(rel))[0]
    h1 = H1_RE.search(body)
    title = h1.group(1).strip() if h1 else stem
    tags = fm.get("tags", []) if isinstance(fm.get("tags"), list) else []
    links = {t for t in (link_target(m) for m in LINK_RE.findall(body)) if t}
    return Note(path=rel, stem=stem, type=fm.get("type", ""), title=title,
                tags=tags, body=body, links=links)


def load_snapshot(root: str) -> list[Note]:
    notes: list[Note] = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            notes.append(load_note(full, rel))
    return notes


# ----------------------------------------------------------------------------
# Live vault scanning — read the local vault straight off disk
# ----------------------------------------------------------------------------

def obsidian_config_path() -> str | None:
    """Path to Obsidian's obsidian.json, which maps each known vault to its
    absolute path and flags which are open. The Local REST API never exposes
    this path, so this config file is how we discover the vault root."""
    home = os.path.expanduser("~")
    system = platform.system()
    if system == "Darwin":
        return os.path.join(home, "Library", "Application Support", "obsidian", "obsidian.json")
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        return os.path.join(appdata, "obsidian", "obsidian.json") if appdata else None
    return os.path.join(home, ".config", "obsidian", "obsidian.json")  # linux / other


def vault_root_from_obsidian_config() -> str | None:
    """Best-effort vault root from obsidian.json: the sole open vault, or the
    sole vault if only one is registered. Ambiguity returns None (caller errors)."""
    cfg = obsidian_config_path()
    if not cfg or not os.path.isfile(cfg):
        return None
    try:
        with open(cfg, encoding="utf-8") as f:
            vaults = (json.load(f) or {}).get("vaults", {})
    except (OSError, json.JSONDecodeError):
        return None
    paths = [v["path"] for v in vaults.values() if v.get("path")]
    open_paths = [v["path"] for v in vaults.values() if v.get("open") and v.get("path")]
    if len(open_paths) == 1:
        return open_paths[0]
    if len(paths) == 1:
        return paths[0]
    return None


def resolve_vault_root(explicit: str | None) -> str:
    """Resolve the vault root in precedence order: --vault-path, then
    $OBSIDIAN_VAULT_PATH, then Obsidian's obsidian.json. Exit with guidance if
    none resolves — never guess."""
    for candidate in (explicit, os.environ.get("OBSIDIAN_VAULT_PATH"),
                       vault_root_from_obsidian_config()):
        if candidate:
            return os.path.abspath(os.path.expanduser(candidate))
    raise SystemExit(
        "could not resolve the Obsidian vault root.\n"
        "  Pass --vault-path /abs/path, set OBSIDIAN_VAULT_PATH, or open exactly\n"
        "  one vault in Obsidian so obsidian.json is unambiguous."
    )


def load_from_vault(root: str, dirs: list[str]) -> list[Note]:
    """Walk the named subdirs under the vault root, loading each .md as a Note.
    Paths are reported relative to the root (e.g. 'notes/http2.md') so results
    read the same as the snapshot mode. Only the requested subdirs are scanned,
    so inbox/, _templates/, _artifacts/ never pollute the analysis."""
    notes: list[Note] = []
    for sub in dirs:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for name in files:
                if not name.endswith(".md"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root)
                notes.append(load_note(full, rel))
    return notes


# ----------------------------------------------------------------------------
# Tokenization helpers — available to the near-dup scorer
# ----------------------------------------------------------------------------

def title_tokens(note: Note) -> set[str]:
    """Lowercased word tokens of a note's title."""
    return {w.lower() for w in WORD_RE.findall(note.title)}


def body_shingles(note: Note, k: int = 3) -> set[str]:
    """Set of k-word shingles over the note body (lowercased)."""
    words = [w.lower() for w in WORD_RE.findall(note.body)]
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def jaccard(a: set, b: set) -> float:
    """|A ∩ B| / |A ∪ B|, with empty-set guard."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# ----------------------------------------------------------------------------
# Near-duplicate scoring
# ----------------------------------------------------------------------------

# How much the title (vs. body) drives the score. Golden-ratio split: titles
# are the higher-precision signal, so they carry the majority of the weight.
TITLE_WEIGHT = 0.618

# Combined score at or above this proposes a merge. Deliberately high — a
# false-positive merge proposal is more disruptive than a missed near-dup,
# which fits the vault's curation-over-accumulation philosophy.
NEAR_DUP_THRESHOLD = 0.5


def similarity(a: Note, b: Note) -> float:
    """Return a 0..1 near-duplicate score: a TITLE_WEIGHT-weighted blend of
    title-token overlap and body-shingle overlap (both Jaccard).

    Because the weights sum to 1 and each Jaccard is already 0..1, the result
    is a convex combination that stays in 0..1 — no clamping needed.

    Title overlap is high-precision but brittle to rewording; body overlap is
    the reverse. The blend lets a strong title match dominate while body
    agreement still pushes borderline pairs over the line. An empty stub body
    scores 0 on the body term, so a stub is matched on title alone — exactly
    right for an unfilled note that duplicates a real one.
    """
    title_score = jaccard(title_tokens(a), title_tokens(b))
    body_score = jaccard(body_shingles(a), body_shingles(b))
    return TITLE_WEIGHT * title_score + (1 - TITLE_WEIGHT) * body_score


# ----------------------------------------------------------------------------
# Analyses
# ----------------------------------------------------------------------------

def find_orphans(notes: list[Note]) -> list[Note]:
    indeg: dict[str, int] = {n.stem: 0 for n in notes}
    for n in notes:
        for target in n.links:
            if target in indeg and target != n.stem:
                indeg[target] += 1
    return [n for n in notes if n.type == "note" and indeg.get(n.stem, 0) == 0]


def find_moc_gaps(notes: list[Note], threshold: int) -> list[dict]:
    moc_tags: set[str] = set()
    tag_members: dict[str, list[str]] = {}
    for n in notes:
        if n.type == "moc":
            moc_tags.update(n.tags)
        if n.type == "note":
            for tag in n.tags:
                tag_members.setdefault(tag, []).append(n.stem)
    gaps = []
    for tag, members in tag_members.items():
        if len(members) >= threshold and tag not in moc_tags:
            gaps.append({"tag": tag, "count": len(members),
                         "members": sorted(members)})
    return sorted(gaps, key=lambda g: g["count"], reverse=True)


def find_near_dups(notes: list[Note], threshold: float) -> list[dict]:
    candidates = [n for n in notes if n.type not in NON_ATOMIC]
    pairs = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            score = similarity(candidates[i], candidates[j])
            if score >= threshold:
                pairs.append({"a": candidates[i].stem,
                              "b": candidates[j].stem,
                              "score": round(score, 3)})
    return sorted(pairs, key=lambda p: p["score"], reverse=True)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault-path", help="Vault root to scan directly "
                        "(default: $OBSIDIAN_VAULT_PATH, else Obsidian's obsidian.json)")
    parser.add_argument("--dirs", default="notes,moc",
                        help="Comma-separated subdirs to scan under the vault root "
                             "(default: notes,moc)")
    parser.add_argument("--snapshot", help="Offline fallback: analyze a prebuilt "
                        "snapshot tree of .md files instead of the live vault")
    parser.add_argument("--moc-threshold", type=int, default=5,
                        help="Min notes sharing a tag to flag a MOC gap (default: 5)")
    parser.add_argument("--dup-threshold", type=float, default=NEAR_DUP_THRESHOLD,
                        help=f"Min similarity to propose a merge (default: {NEAR_DUP_THRESHOLD})")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    if args.snapshot:
        if not os.path.isdir(args.snapshot):
            print(f"snapshot dir not found: {args.snapshot}", file=sys.stderr)
            return 1
        notes = load_snapshot(args.snapshot)
        source = args.snapshot
    else:
        root = resolve_vault_root(args.vault_path)
        if not os.path.isdir(root):
            print(f"vault root not found: {root}", file=sys.stderr)
            return 1
        dirs = [d.strip() for d in args.dirs.split(",") if d.strip()]
        notes = load_from_vault(root, dirs)
        source = root

    by_type: dict[str, int] = {}
    for n in notes:
        by_type[n.type or "(none)"] = by_type.get(n.type or "(none)", 0) + 1

    orphans = find_orphans(notes)
    moc_gaps = find_moc_gaps(notes, args.moc_threshold)
    near_dups = find_near_dups(notes, args.dup_threshold)

    result = {
        "summary": {"source": source, "notes": len(notes), "by_type": by_type},
        "orphans": [{"path": n.path, "stem": n.stem, "title": n.title, "tags": n.tags}
                    for n in orphans],
        "moc_gaps": moc_gaps,
        "near_dup_pairs": near_dups,
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"notes: {len(notes)}  types: {by_type}")
        print(f"\norphans ({len(orphans)}):")
        for n in orphans:
            print(f"  - {n.stem}  [{', '.join(n.tags)}]")
        print(f"\nMOC gaps ({len(moc_gaps)}):")
        for g in moc_gaps:
            print(f"  - {g['tag']}  ({g['count']} notes): {', '.join(g['members'])}")
        print(f"\nnear-dup pairs ({len(near_dups)}):")
        for p in near_dups:
            print(f"  - {p['a']} ~ {p['b']}  ({p['score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
