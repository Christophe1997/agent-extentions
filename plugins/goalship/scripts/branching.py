"""Branch operations.

Every operation below is additive-only: create a branch, commit, push,
reset a branch this script itself created back to a clean base. There is
no merge, approve, force-push, arbitrary branch-delete, or publish code
path anywhere in this module — asserted directly against every
scripts/*.py's source (this one included) in tests/test_branching.py,
not just documented here.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import reconciliation
import run_state


@dataclass
class DependencyPR:
    """A predecessor ticket's linked PR, as recorded in its closing note."""
    ticket_id: str
    branch: str
    state: str  # "open" | "merged" | "closed"


def resolve_branch_base(trunk_branch: str, dependency_prs: list) -> str:
    """Dependency-aware branch model:
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
    matches = reconciliation.tk_query(repo_root, f'select(.id=="{ticket_id}")')
    dep_ids = matches[0].get("deps", []) if matches else []

    dependency_prs = []
    for dep_id in dep_ids:
        fields = reconciliation.note_fields_for_ticket(repo_root, dep_id)
        branch = fields.get("branch")
        if not branch:
            continue
        pr_ref = fields.get("pr")
        if not pr_ref:
            # No PR was ever recorded for this predecessor — legitimately
            # resolved, same as a merged/closed one.
            state = "closed"
        else:
            state = reconciliation.pr_state(repo_root, host_tool, pr_ref)
            if state is None:
                # The lookup itself failed (expired credential, host
                # outage) — distinct from a legitimately closed PR.
                # Folding this into "closed" would silently rebase
                # `ticket_id` onto trunk instead of dep_id's still-open
                # branch, so surface it as a loud error instead.
                raise RuntimeError(
                    f"could not resolve base for {ticket_id!r}: pr_state lookup "
                    f"failed for dependency {dep_id!r} (pr: {pr_ref!r})"
                )
        dependency_prs.append(DependencyPR(ticket_id=dep_id, branch=branch, state=state))

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
    local and origin/ refs."""
    base = f"{ticket_type}/{slugify(title)}"
    existing = _all_branch_names(Path(repo_root))
    if base not in existing:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    return f"{base}-{suffix}"


def local_branch_exists(repo_root: Path, branch_name: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        cwd=repo_root, capture_output=True, text=True,
    )
    return result.returncode == 0


def create_branch(repo_root: Path, branch_name: str, base_ref: str) -> None:
    """Create branch_name off base_ref and check it out. Called at claim
    time, before implementation starts, so a crash mid-implementation
    never leaves work sitting on trunk."""
    subprocess.run(
        ["git", "checkout", "-b", branch_name, base_ref],
        cwd=repo_root, check=True, capture_output=True,
    )


def commit_all(repo_root: Path, message: str) -> str:
    """Stage everything except this tool's own state dirs and commit;
    returns the new head SHA. .goalship/ and .tickets/ are excluded so a
    ticket's PR carries only its own implementation diff, never this
    loop's or tk's own bookkeeping churn.

    .goalship/ is excluded by ensuring it's git-ignored rather than
    with an explicit `git add` negative pathspec: once an entry is in
    .git/info/exclude, git's own "ignored file" advice makes `git add`
    exit nonzero for any pathspec that names that path explicitly, even a
    negative one — confirmed against a real repo. .tickets/ is never made
    git-ignored (that's the target repo's own call), so it still
    needs the explicit negative pathspec.
    """
    run_state.ensure_ledger_excluded(repo_root)
    subprocess.run(
        ["git", "add", "-A", "--", ".", f":!{run_state.TICKETS_DIR_NAME}"],
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
    the request, it never pushes. PR creation is a safety-critical
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

    result = subprocess.run(
        argv, cwd=repo_root, capture_output=True, text=True, check=True,
        timeout=run_state.HOST_TOOL_TIMEOUT_SECONDS,
    )
    for line in reversed(result.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            return line
    raise RuntimeError(f"{host_tool} pr create did not print a URL: {result.stdout!r}")


def retarget_pull_request(repo_root: Path, host_tool: str, pr_ref: str, new_base: str) -> None:
    """Change an already-open PR/MR's base branch — the
    retarget_base_merged outcome: a stacked ticket's dependency merged out
    from under its open PR, so the PR must repoint at trunk (or a further
    dependency) instead of the now-gone branch."""
    if host_tool == "gh":
        argv = ["gh", "pr", "edit", pr_ref, "--base", new_base]
    elif host_tool == "glab":
        argv = ["glab", "mr", "update", pr_ref, "--target-branch", new_base]
    else:
        raise ValueError(f"unsupported host_tool: {host_tool!r}")
    subprocess.run(
        argv, cwd=repo_root, check=True, capture_output=True,
        timeout=run_state.HOST_TOOL_TIMEOUT_SECONDS,
    )


def head_sha(repo_root: Path, ref: str = "HEAD") -> str:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def commit_landed_since(repo_root: Path, branch: str, claim_sha: str) -> bool:
    """Whether `branch`'s tip has moved since `claim_sha` — a ticket-scoped
    crash-recovery check for retry_pr_creation. `claim_sha` is the
    branch's tip at the moment a ticket claimed it (record_claim_note's
    claim_sha field): a true result means a commit landed after that
    point. Ticket-scoped, not branch-wide: a branch that also carries
    other tickets' already-landed commits (a shared branch under commit
    mode) can't fool this the way a bare "any commits past base at all"
    check would."""
    return head_sha(repo_root, branch) != claim_sha


def reset_to_clean_base(repo_root: Path, base_branch: str) -> None:
    """Abort cleanup: on a gate failure or interruption, return to a
    clean checkout of base_branch (trunk, or a stacked ticket's parent
    branch) before the loop claims its next ticket. Resets and cleans only
    the working tree the script itself was using for the aborted ticket's
    branch — it never deletes that branch.

    `git clean -fd` alone would delete .tickets/ along with any other
    untracked scratch: .tickets/ is never git-ignored by this tool,
    so a plain clean wipes out the entire ticket store on the very first
    gate failure — confirmed against a real repo. -e excludes it from the
    sweep the same way `.goalship/`'s own .git/info/exclude entry already
    protects it.
    """
    subprocess.run(["git", "checkout", base_branch], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "clean", "-fd", "-e", run_state.TICKETS_DIR_NAME],
        cwd=repo_root, check=True, capture_output=True,
    )
