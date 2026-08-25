#!/usr/bin/env python3
"""Backing script for goalship (KTD1): deterministic git/tk/gh mechanics
and the durable run-state ledger. The skill runs and interprets the
target repo's gate commands itself — this script never wraps gate
execution, so gate output stays visible in the transcript.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
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


def dirty_paths(repo_root: Path) -> list:
    """Repo-relative paths git considers dirty, excluding the ledger dir itself
    (KTD5 defense-in-depth: writing the ledger must never trip this check)."""
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        relpath = line[3:].strip()
        if relpath.startswith(f"{LEDGER_DIR_NAME}/") or relpath == LEDGER_DIR_NAME:
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
    """Stage everything and commit; returns the new head SHA."""
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True, capture_output=True)
    return head_sha(repo_root)


def push_branch(repo_root: Path, branch_name: str) -> None:
    """Push branch_name and set it to track origin. Never force."""
    subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        cwd=repo_root, check=True, capture_output=True,
    )


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
