#!/usr/bin/env python3
"""Backing script for goalship (KTD1): deterministic git/tk/gh mechanics
and the durable run-state ledger. The skill runs and interprets the
target repo's gate commands itself — this script never wraps gate
execution, so gate output stays visible in the transcript.

Run standalone (`loop_runner.py <subcommand> ...`, see USAGE below) for
the CLI surface skills/goalship/references/execution-loop.md drives; import
directly (as the tests do) to use the functions themselves.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# KTD9: fixed v1 caps, not user-configurable, reset per invocation (not persisted).
SHIP_CAP = 10
FAILURE_CAP = 3

# KTD2: ledger lives inside the target repo's own working tree, excluded
# from git via .git/info/exclude rather than relying on the repo's .gitignore.
LEDGER_DIR_NAME = ".goalship"

# tk's own state directory. Excluded from this tool's dirty-tree check and
# commit staging for the same reason as LEDGER_DIR_NAME: `tk start`/`tk
# add-note` mutate it as a routine side effect of running this very loop,
# unrelated to a ticket's implementation diff. Whether the target repo
# tracks .tickets/ at all is that repo's own decision (R10) — this only
# keeps the loop's own commits and clean-tree checks from reacting to it.
TICKETS_DIR_NAME = ".tickets"


@dataclass
class RunState:
    run_id: str
    shipped_count: int = 0
    consecutive_failures: int = 0
    claimed_ticket_ids: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "shipped_count": self.shipped_count,
            "consecutive_failures": self.consecutive_failures,
            "claimed_ticket_ids": list(self.claimed_ticket_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RunState":
        return cls(
            run_id=data["run_id"],
            shipped_count=data.get("shipped_count", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            claimed_ticket_ids=list(data.get("claimed_ticket_ids", [])),
        )


def generate_run_id() -> str:
    """A fresh, opaque run identifier for a new invocation."""
    return uuid.uuid4().hex[:12]


def resolve_ledger_path(repo_root: Path, run_id: str) -> Path:
    """Resolve the on-disk path holding this run's ledger state.

    One file per run_id, rather than one shared file keyed internally by
    run_id: a shared file needs read-modify-write locking to avoid a
    lost-update race between concurrent invocations (two processes each
    read the old file, then each write back a version missing the
    other's update) — this repo's own yapermission plugin hit exactly
    that class of bug twice (KTD2) before landing on per-partition files.
    One file per run_id makes the race structurally impossible: distinct
    run_ids never contend for the same inode.
    """
    safe_run_id = re.sub(r"[^A-Za-z0-9._-]", "_", run_id) or "run"
    return Path(repo_root) / LEDGER_DIR_NAME / f"{safe_run_id}.json"


def load_run_state(repo_root: Path, run_id: str) -> RunState:
    """Read run_id's ledger, or a fresh zeroed state if none exists yet."""
    path = resolve_ledger_path(Path(repo_root), run_id)
    if not path.exists():
        return RunState(run_id=run_id)
    return RunState.from_dict(json.loads(path.read_text()))


def save_run_state(repo_root: Path, state: RunState) -> None:
    """Persist state atomically (write-to-temp + rename) so a crash
    mid-write never leaves a corrupt or half-written ledger."""
    path = resolve_ledger_path(Path(repo_root), state.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(state.to_dict(), indent=2))
    tmp_path.replace(path)


def record_ship(state: RunState) -> None:
    """A successful ship resets the consecutive-failure count (KTD9)."""
    state.shipped_count += 1
    state.consecutive_failures = 0


def record_failure(state: RunState) -> None:
    """A gate failure or a block both count toward the consecutive-failure cap (KTD9)."""
    state.consecutive_failures += 1


def claim_ticket(state: RunState, ticket_id: str) -> None:
    if ticket_id not in state.claimed_ticket_ids:
        state.claimed_ticket_ids.append(ticket_id)


def is_claimed(state: RunState, ticket_id: str) -> bool:
    return ticket_id in state.claimed_ticket_ids


def caps_exceeded(state: RunState) -> Optional[str]:
    """None when under both caps; otherwise the human-readable reason to stop (R9)."""
    if state.shipped_count >= SHIP_CAP:
        return f"ship cap reached ({SHIP_CAP} tickets shipped this run)"
    if state.consecutive_failures >= FAILURE_CAP:
        return f"consecutive-failure cap reached ({FAILURE_CAP} failures in a row)"
    return None


def ensure_ledger_excluded(repo_root: Path) -> None:
    """Add the ledger dir to .git/info/exclude if it isn't already there (KTD2)."""
    exclude_file = Path(repo_root) / ".git" / "info" / "exclude"
    entry = f"/{LEDGER_DIR_NAME}/"
    existing = exclude_file.read_text() if exclude_file.exists() else ""
    if entry in existing.splitlines():
        return
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    with exclude_file.open("a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(entry + "\n")


_IGNORED_DIRTY_DIR_NAMES = (LEDGER_DIR_NAME, TICKETS_DIR_NAME)


def dirty_paths(repo_root: Path) -> list:
    """Repo-relative paths git considers dirty, excluding the ledger dir and
    tk's own state dir (KTD5 defense-in-depth: writing the ledger, or tk
    mutating its own files, must never trip this check)."""
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        relpath = line[3:].strip()
        if any(relpath == name or relpath.startswith(f"{name}/") for name in _IGNORED_DIRTY_DIR_NAMES):
            continue
        paths.append(relpath)
    return paths


def _git_remote_url(repo_root: Path) -> Optional[str]:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _resolve_trunk_branch(repo_root: Path) -> Optional[str]:
    """origin/HEAD when resolvable, else a local main/master, else the current branch."""
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode == 0:
        ref = result.stdout.strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref[len("refs/remotes/origin/"):]

    for candidate in ("main", "master"):
        check = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"],
            cwd=repo_root, capture_output=True,
        )
        if check.returncode == 0:
            return candidate

    current = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root, capture_output=True, text=True,
    )
    return current.stdout.strip() or None


def _detect_host_tool() -> Optional[str]:
    for tool in ("gh", "glab"):
        if shutil.which(tool):
            return tool
    return None


def _host_tool_authenticated(tool: str) -> bool:
    result = subprocess.run([tool, "auth", "status"], capture_output=True)
    return result.returncode == 0


@dataclass
class PreflightResult:
    ok: bool
    remote_url: Optional[str] = None
    trunk_branch: Optional[str] = None
    host_tool: Optional[str] = None
    failures: list = field(default_factory=list)


def run_preflight(repo_root: Path, will_create_prs: bool) -> PreflightResult:
    """KTD5 preconditions: tk present, remote configured, clean tree, and
    (only when PR creation will run) an authenticated gh/glab. Never
    counted against R9's failure cap — this fails the whole run, not one ticket."""
    repo_root = Path(repo_root)
    failures = []

    if shutil.which("tk") is None:
        failures.append("tk (ticket) not found on PATH")

    remote_url = _git_remote_url(repo_root)
    if not remote_url:
        failures.append("no git remote 'origin' configured")

    dirty = dirty_paths(repo_root)
    if dirty:
        failures.append("working tree is dirty: " + ", ".join(dirty))

    host_tool = None
    if will_create_prs:
        host_tool = _detect_host_tool()
        if host_tool is None:
            failures.append("neither gh nor glab found on PATH")
        elif not _host_tool_authenticated(host_tool):
            failures.append(f"{host_tool} is not authenticated (run `{host_tool} auth login`)")

    trunk_branch = _resolve_trunk_branch(repo_root) if not failures else None

    return PreflightResult(
        ok=not failures,
        remote_url=remote_url,
        trunk_branch=trunk_branch,
        host_tool=host_tool,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Branch operations (KTD3, KTD4, R4, R5, R8).
#
# Every operation below is additive-only: create a branch, commit, push,
# reset a branch this script itself created back to a clean base. There is
# no merge, approve, force-push, arbitrary branch-delete, or publish code
# path anywhere in this module (R8) — asserted directly against the source
# in tests/test_branching.py, not just documented here.
# ---------------------------------------------------------------------------

@dataclass
class DependencyPR:
    """A predecessor ticket's linked PR, as recorded in its closing note (R5)."""
    ticket_id: str
    branch: str
    state: str  # "open" | "merged" | "closed"


def resolve_branch_base(trunk_branch: str, dependency_prs: list) -> str:
    """Dependency-aware branch model (Product Contract Key Decision, R4/R6):
    trunk by default; a single still-open predecessor's branch when exactly
    one predecessor has an open PR; trunk on fan-in (two or more
    simultaneously open predecessors) or when no predecessor has an open PR
    (merged, closed, or no dependencies at all) — git supports only one base
    per branch, and trunk is the only base every predecessor's eventual
    merge converges on.
    """
    open_preds = [d for d in dependency_prs if d.state == "open"]
    if len(open_preds) == 1:
        return open_preds[0].branch
    return trunk_branch


def resolve_base_for_ticket(
    repo_root: Path, ticket_id: str, trunk_branch: str, host_tool: Optional[str] = None,
) -> str:
    """Look up `ticket_id`'s tk dependencies (which stay in `deps` even once
    resolved — closed status, not array membership, marks them resolved)
    and apply the dependency-aware branch model. A predecessor with no
    recorded branch note (closed by hand, or predating this loop) can't be
    looked up and is treated as resolved, same as a merged one."""
    repo_root = Path(repo_root)
    matches = tk_query(repo_root, f'select(.id=="{ticket_id}")')
    dep_ids = matches[0].get("deps", []) if matches else []

    dependency_prs = []
    for dep_id in dep_ids:
        fields = note_fields_for_ticket(repo_root, dep_id)
        branch = fields.get("branch")
        if not branch:
            continue
        pr_ref = fields.get("pr")
        state = pr_state(repo_root, host_tool, pr_ref) if pr_ref else "closed"
        dependency_prs.append(DependencyPR(ticket_id=dep_id, branch=branch, state=state or "closed"))

    return resolve_branch_base(trunk_branch, dependency_prs)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def _all_branch_names(repo_root: Path) -> set:
    """Local branch names plus origin/* remote-tracking branch names,
    short-formed — so a branch that exists only on origin (e.g. left by a
    prior run) still counts as taken."""
    result = subprocess.run(
        ["git", "branch", "-a", "--format=%(refname:short)"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    names = set()
    for line in result.stdout.splitlines():
        name = line.strip()
        if name.startswith("origin/"):
            name = name[len("origin/"):]
        if name and name != "HEAD":
            names.add(name)
    return names


def branch_name_for_ticket(repo_root: Path, ticket_type: str, title: str) -> str:
    """`<type>/<slug>`, with a numeric collision suffix checked against
    local and origin/ refs (KTD3)."""
    base = f"{ticket_type}/{slugify(title)}"
    existing = _all_branch_names(Path(repo_root))
    if base not in existing:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    return f"{base}-{suffix}"


def create_branch(repo_root: Path, branch_name: str, base_ref: str) -> None:
    """Create branch_name off base_ref and check it out. Called at claim
    time, before implementation starts (KTD4), so a crash mid-implementation
    never leaves work sitting on trunk."""
    subprocess.run(
        ["git", "checkout", "-b", branch_name, base_ref],
        cwd=repo_root, check=True, capture_output=True,
    )


def commit_all(repo_root: Path, message: str) -> str:
    """Stage everything except this tool's own state dirs and commit;
    returns the new head SHA. .goalship/ and .tickets/ are excluded so a
    ticket's PR carries only its own implementation diff, never this
    loop's or tk's own bookkeeping churn."""
    exclude_pathspecs = [f":!{name}" for name in _IGNORED_DIRTY_DIR_NAMES]
    subprocess.run(
        ["git", "add", "-A", "--", ".", *exclude_pathspecs],
        cwd=repo_root, check=True, capture_output=True,
    )
    subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True, capture_output=True)
    return head_sha(repo_root)


def push_branch(repo_root: Path, branch_name: str) -> None:
    """Push branch_name and set it to track origin. Never force."""
    subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        cwd=repo_root, check=True, capture_output=True,
    )


def create_pull_request(
    repo_root: Path,
    host_tool: str,
    branch: str,
    base: str,
    title: str,
    body: str,
) -> str:
    """Open a pull/merge request for `branch` against `base`; returns its
    URL. `branch` must already be pushed (push_branch) — this only opens
    the request, it never pushes. KTD1: PR creation is a safety-critical
    mechanical operation, so it lives here rather than in skill prose."""
    if host_tool == "gh":
        argv = [
            "gh", "pr", "create",
            "--head", branch, "--base", base,
            "--title", title, "--body", body,
        ]
    elif host_tool == "glab":
        argv = [
            "glab", "mr", "create",
            "--source-branch", branch, "--target-branch", base,
            "--title", title, "--description", body, "--yes",
        ]
    else:
        raise ValueError(f"unsupported host_tool: {host_tool!r}")

    result = subprocess.run(argv, cwd=repo_root, capture_output=True, text=True, check=True)
    for line in reversed(result.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            return line
    raise RuntimeError(f"{host_tool} pr create did not print a URL: {result.stdout!r}")


def head_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def reset_to_clean_base(repo_root: Path, base_branch: str) -> None:
    """Abort cleanup (KTD4): on a gate failure or interruption, return to a
    clean checkout of base_branch (trunk, or a stacked ticket's parent
    branch) before the loop claims its next ticket. Resets and cleans only
    the working tree the script itself was using for the aborted ticket's
    branch — it never deletes that branch."""
    subprocess.run(["git", "checkout", base_branch], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "clean", "-fd"], cwd=repo_root, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# tk mechanics and loop-start reconciliation (KTD8, R5, R12).
#
# `tk` auto-discovers `.tickets/` by walking up from cwd (same mechanism
# git uses for `.git/`), so every wrapper below just runs with cwd=repo_root
# rather than managing TICKETS_DIR itself.
# ---------------------------------------------------------------------------

_KV_LINE_RE = re.compile(r"^([a-zA-Z_]+):\s*(.+)$")
_NOTES_HEADING_RE = re.compile(r"^## Notes\s*$", re.MULTILINE)
_NEXT_HEADING_RE = re.compile(r"^## \S", re.MULTILINE)
_NOTE_MARKER_RE = re.compile(r"^\*\*[^*]+\*\*\s*$", re.MULTILINE)


def tk_query(repo_root: Path, jq_filter: str = ".") -> list:
    result = subprocess.run(
        ["tk", "query", jq_filter], cwd=repo_root, capture_output=True, text=True, check=True,
    )
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def tk_in_progress_tickets(repo_root: Path) -> list:
    return tk_query(repo_root, 'select(.status=="in_progress")')


def tk_add_note(repo_root: Path, ticket_id: str, text: str) -> None:
    subprocess.run(["tk", "add-note", ticket_id, text], cwd=repo_root, check=True, capture_output=True)


def tk_close(repo_root: Path, ticket_id: str) -> None:
    subprocess.run(["tk", "close", ticket_id], cwd=repo_root, check=True, capture_output=True)


def tk_reopen(repo_root: Path, ticket_id: str) -> None:
    subprocess.run(["tk", "reopen", ticket_id], cwd=repo_root, check=True, capture_output=True)


def record_claim_note(repo_root: Path, ticket_id: str, branch: str, base: Optional[str] = None) -> None:
    """Written at claim time (KTD4), before implementation starts — the only
    record of a ticket's branch that survives a crash before any later note."""
    lines = [f"branch: {branch}"]
    if base:
        lines.append(f"base: {base}")
    tk_add_note(repo_root, ticket_id, "\n".join(lines))


def record_ship_note(repo_root: Path, ticket_id: str, branch: str, pr_url: str, sha: str) -> None:
    """R5: on success, the closing note records branch, PR URL, and head SHA."""
    tk_add_note(repo_root, ticket_id, f"branch: {branch}\npr: {pr_url}\nsha: {sha}")


def _notes_section(show_output: str) -> str:
    heading = _NOTES_HEADING_RE.search(show_output)
    if not heading:
        return ""
    rest = show_output[heading.end():]
    next_heading = _NEXT_HEADING_RE.search(rest)
    return rest[:next_heading.start()] if next_heading else rest


def tk_show_notes(repo_root: Path, ticket_id: str) -> list:
    """Raw text of each note on a ticket, oldest first."""
    result = subprocess.run(
        ["tk", "show", ticket_id], cwd=repo_root, capture_output=True, text=True, check=True,
    )
    section = _notes_section(result.stdout)
    markers = list(_NOTE_MARKER_RE.finditer(section))
    notes = []
    for i, marker in enumerate(markers):
        start = marker.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(section)
        notes.append(section[start:end].strip())
    return notes


def _parse_key_value_note(note_text: str) -> dict:
    """A note qualifies as machine-readable only if every non-blank line is
    `key: value` — a prose reconciliation note never gets misread as data."""
    lines = [line.strip() for line in note_text.splitlines() if line.strip()]
    if not lines:
        return {}
    fields = {}
    for line in lines:
        m = _KV_LINE_RE.match(line)
        if not m:
            return {}
        fields[m.group(1)] = m.group(2).strip()
    return fields


def note_fields_for_ticket(repo_root: Path, ticket_id: str) -> dict:
    """Key/value fields merged across all of a ticket's structured notes,
    oldest to newest, so a later note's fields extend or override an
    earlier one's (e.g. a claim-time `branch:` note, then a ship-time note
    that adds `pr:`/`sha:`)."""
    fields = {}
    for note in tk_show_notes(repo_root, ticket_id):
        fields.update(_parse_key_value_note(note))
    return fields


def find_ticket_by_branch(repo_root: Path, branch: str) -> Optional[str]:
    for ticket in tk_query(repo_root, "."):
        if note_fields_for_ticket(repo_root, ticket["id"]).get("branch") == branch:
            return ticket["id"]
    return None


def pr_state(repo_root: Path, host_tool: Optional[str], pr_ref: str) -> Optional[str]:
    """"open" | "merged" | "closed", or None when the lookup itself failed
    (e.g. an expired credential) — kept distinct from a legitimately
    non-open PR so callers don't misreport "can't tell" as "not open"."""
    if host_tool == "gh":
        result = subprocess.run(
            ["gh", "pr", "view", pr_ref, "--json", "state", "-q", ".state"],
            cwd=repo_root, capture_output=True, text=True,
        )
        raw = result.stdout.strip() if result.returncode == 0 else ""
    elif host_tool == "glab":
        result = subprocess.run(
            ["glab", "mr", "view", pr_ref, "-F", "json"],
            cwd=repo_root, capture_output=True, text=True,
        )
        raw = ""
        if result.returncode == 0:
            try:
                raw = json.loads(result.stdout).get("state", "")
            except json.JSONDecodeError:
                raw = ""
    else:
        return None

    return {
        "OPEN": "open", "MERGED": "merged", "CLOSED": "closed",
        "opened": "open", "merged": "merged", "closed": "closed",
    }.get(raw)


@dataclass
class ReconciliationAction:
    ticket_id: str
    outcome: str
    detail: str = ""


@dataclass
class ReconciliationReport:
    actions: list = field(default_factory=list)
    auth_failure: Optional[str] = None


def reconcile(repo_root: Path) -> ReconciliationReport:
    """KTD8: cross-check every in-progress ticket against git/PR state
    before the next `tk ready` pick.

    Always queries tk directly for the in-progress set — the durable
    source of truth for ticket status — rather than the run-state ledger,
    so R12's "fall back to tk's own in-progress tickets when the ledger is
    missing or corrupted" holds by construction: this function has no
    ledger dependency to fall back from in the first place.
    """
    repo_root = Path(repo_root)
    tickets_with_fields = [
        (ticket["id"], note_fields_for_ticket(repo_root, ticket["id"]))
        for ticket in tk_in_progress_tickets(repo_root)
    ]

    needs_host_lookup = any(
        fields.get("pr") or fields.get("branch") for _, fields in tickets_with_fields
    )
    host_tool = None
    if needs_host_lookup:
        host_tool = _detect_host_tool()
        if host_tool is None or not _host_tool_authenticated(host_tool):
            # KTD8: a credential that keeps failing routes to a
            # preflight-class stop instead of retrying per ticket without limit.
            return ReconciliationReport(auth_failure=host_tool or "gh/glab")

    actions = []
    for ticket_id, fields in tickets_with_fields:
        pr_ref = fields.get("pr")
        branch = fields.get("branch")
        base = fields.get("base")

        if not pr_ref:
            if branch:
                actions.append(ReconciliationAction(ticket_id, "retry_pr_creation", branch))
            else:
                actions.append(ReconciliationAction(ticket_id, "no_recoverable_state"))
            continue

        state = pr_state(repo_root, host_tool, pr_ref)
        if state == "merged":
            tk_add_note(repo_root, ticket_id, f"Reconciliation: PR {pr_ref} merged externally; closing.")
            tk_close(repo_root, ticket_id)
            actions.append(ReconciliationAction(ticket_id, "closed_merged", pr_ref))
        elif state == "closed":
            tk_add_note(repo_root, ticket_id, f"Reconciliation: PR {pr_ref} closed without merging; left open.")
            tk_reopen(repo_root, ticket_id)
            actions.append(ReconciliationAction(ticket_id, "failed_closed_unmerged", pr_ref))
        elif state == "open":
            if base:
                base_ticket_id = find_ticket_by_branch(repo_root, base)
                base_fields = note_fields_for_ticket(repo_root, base_ticket_id) if base_ticket_id else {}
                base_pr = base_fields.get("pr")
                base_state = pr_state(repo_root, host_tool, base_pr) if base_pr else None
                if base_state == "merged":
                    actions.append(ReconciliationAction(ticket_id, "retarget_base_merged", base))
                elif base_state == "closed":
                    tk_add_note(
                        repo_root, ticket_id,
                        f"Reconciliation: base {base} closed without merging; blocked.",
                    )
                    actions.append(ReconciliationAction(ticket_id, "blocked_stale_base", base))
        else:
            actions.append(ReconciliationAction(ticket_id, "pr_state_unresolved", pr_ref))

    return ReconciliationReport(actions=actions)


# ---------------------------------------------------------------------------
# CLI dispatcher — the skill's invocation surface. Each cmd_* function is a
# thin argv-to-function-call adapter; the logic itself lives in the tested
# functions above, mirroring this repo's yapermission/a2a script convention.
# ---------------------------------------------------------------------------

USAGE = """Usage:
  loop_runner.py preflight <repo_root> <true|false>
  loop_runner.py reconcile <repo_root>
  loop_runner.py ledger <repo_root> [--run-id ID] [--claim TICKET_ID] [--ship] [--fail]
  loop_runner.py dirty <repo_root>
  loop_runner.py branch-name <repo_root> <type> <title>
  loop_runner.py resolve-base <repo_root> <ticket_id> <trunk_branch> [host_tool]
  loop_runner.py claim <repo_root> <ticket_id> <branch_name> <base_ref> <trunk_branch>
  loop_runner.py commit <repo_root> <message>
  loop_runner.py push <repo_root> <branch_name>
  loop_runner.py create-pr <repo_root> <host_tool> <branch> <base> <title> <body>
  loop_runner.py ship <repo_root> <ticket_id> <branch> <pr_url> <sha>
  loop_runner.py reset <repo_root> <base_branch>
"""


def _print_json(data) -> None:
    print(json.dumps(data))


def cmd_preflight(args: list) -> None:
    if len(args) < 2:
        print("error: usage: preflight <repo_root> <true|false>", file=sys.stderr)
        sys.exit(1)
    result = run_preflight(Path(args[0]), args[1].lower() == "true")
    _print_json({
        "ok": result.ok,
        "remote_url": result.remote_url,
        "trunk_branch": result.trunk_branch,
        "host_tool": result.host_tool,
        "failures": result.failures,
    })


def cmd_reconcile(args: list) -> None:
    if len(args) < 1:
        print("error: usage: reconcile <repo_root>", file=sys.stderr)
        sys.exit(1)
    report = reconcile(Path(args[0]))
    _print_json({
        "actions": [
            {"ticket_id": a.ticket_id, "outcome": a.outcome, "detail": a.detail}
            for a in report.actions
        ],
        "auth_failure": report.auth_failure,
    })


def cmd_ledger(args: list) -> None:
    if len(args) < 1:
        print(
            "error: usage: ledger <repo_root> [--run-id ID] [--claim TICKET_ID] [--ship] [--fail]",
            file=sys.stderr,
        )
        sys.exit(1)
    repo_root = Path(args[0])
    run_id = None
    claim_id = None
    ship = False
    fail = False
    rest = args[1:]
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--run-id":
            i += 1
            run_id = rest[i]
        elif tok == "--claim":
            i += 1
            claim_id = rest[i]
        elif tok == "--ship":
            ship = True
        elif tok == "--fail":
            fail = True
        else:
            print(f"error: unknown ledger flag '{tok}'", file=sys.stderr)
            sys.exit(1)
        i += 1

    ensure_ledger_excluded(repo_root)
    state = load_run_state(repo_root, run_id or generate_run_id())
    if claim_id:
        claim_ticket(state, claim_id)
    if ship:
        record_ship(state)
    if fail:
        record_failure(state)
    save_run_state(repo_root, state)

    data = state.to_dict()
    data["caps_exceeded"] = caps_exceeded(state)
    _print_json(data)


def cmd_dirty(args: list) -> None:
    if len(args) < 1:
        print("error: usage: dirty <repo_root>", file=sys.stderr)
        sys.exit(1)
    _print_json(dirty_paths(Path(args[0])))


def cmd_branch_name(args: list) -> None:
    if len(args) < 3:
        print("error: usage: branch-name <repo_root> <type> <title>", file=sys.stderr)
        sys.exit(1)
    print(branch_name_for_ticket(Path(args[0]), args[1], args[2]))


def cmd_resolve_base(args: list) -> None:
    if len(args) < 3:
        print("error: usage: resolve-base <repo_root> <ticket_id> <trunk_branch> [host_tool]", file=sys.stderr)
        sys.exit(1)
    host_tool = args[3] if len(args) > 3 else None
    print(resolve_base_for_ticket(Path(args[0]), args[1], args[2], host_tool))


def cmd_claim(args: list) -> None:
    if len(args) < 5:
        print("error: usage: claim <repo_root> <ticket_id> <branch_name> <base_ref> <trunk_branch>", file=sys.stderr)
        sys.exit(1)
    repo_root, ticket_id, branch_name, base_ref, trunk_branch = Path(args[0]), args[1], args[2], args[3], args[4]
    create_branch(repo_root, branch_name, base_ref)
    record_claim_note(repo_root, ticket_id, branch_name, base=base_ref if base_ref != trunk_branch else None)


def cmd_commit(args: list) -> None:
    if len(args) < 2:
        print("error: usage: commit <repo_root> <message>", file=sys.stderr)
        sys.exit(1)
    print(commit_all(Path(args[0]), args[1]))


def cmd_push(args: list) -> None:
    if len(args) < 2:
        print("error: usage: push <repo_root> <branch_name>", file=sys.stderr)
        sys.exit(1)
    push_branch(Path(args[0]), args[1])


def cmd_create_pr(args: list) -> None:
    if len(args) < 6:
        print("error: usage: create-pr <repo_root> <host_tool> <branch> <base> <title> <body>", file=sys.stderr)
        sys.exit(1)
    repo_root, host_tool, branch, base, title, body = args[0], args[1], args[2], args[3], args[4], args[5]
    print(create_pull_request(Path(repo_root), host_tool, branch, base, title, body))


def cmd_ship(args: list) -> None:
    if len(args) < 5:
        print("error: usage: ship <repo_root> <ticket_id> <branch> <pr_url> <sha>", file=sys.stderr)
        sys.exit(1)
    repo_root, ticket_id, branch, pr_url, sha = Path(args[0]), args[1], args[2], args[3], args[4]
    record_ship_note(repo_root, ticket_id, branch, pr_url, sha)
    tk_close(repo_root, ticket_id)


def cmd_reset(args: list) -> None:
    if len(args) < 2:
        print("error: usage: reset <repo_root> <base_branch>", file=sys.stderr)
        sys.exit(1)
    reset_to_clean_base(Path(args[0]), args[1])


_COMMANDS = {
    "preflight": cmd_preflight,
    "reconcile": cmd_reconcile,
    "ledger": cmd_ledger,
    "dirty": cmd_dirty,
    "branch-name": cmd_branch_name,
    "resolve-base": cmd_resolve_base,
    "claim": cmd_claim,
    "commit": cmd_commit,
    "push": cmd_push,
    "create-pr": cmd_create_pr,
    "ship": cmd_ship,
    "reset": cmd_reset,
}


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    handler = _COMMANDS.get(sys.argv[1])
    if handler is None:
        print(f"error: unknown command '{sys.argv[1]}'\n{USAGE}", file=sys.stderr)
        sys.exit(1)
    try:
        handler(sys.argv[2:])
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        print(f"error: `{' '.join(exc.cmd)}` failed: {stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
