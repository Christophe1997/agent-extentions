"""Preflight checks: repo/remote/host-tool preconditions the loop verifies
once per run (`run_preflight`), plus the dirty-tree check reused at claim
time and by reconciliation's own auth-failure routing.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import run_state

_IGNORED_DIRTY_DIR_NAMES = (run_state.LEDGER_DIR_NAME, run_state.TICKETS_DIR_NAME)


def dirty_paths(repo_root: Path) -> list:
    """Repo-relative paths git considers dirty, excluding the ledger dir and
    tk's own state dir (defense-in-depth: writing the ledger, or tk
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
    result = subprocess.run(
        [tool, "auth", "status"], capture_output=True, timeout=run_state.HOST_TOOL_TIMEOUT_SECONDS,
    )
    return result.returncode == 0


@dataclass
class PreflightResult:
    ok: bool
    remote_url: Optional[str] = None
    trunk_branch: Optional[str] = None
    host_tool: Optional[str] = None
    failures: list = field(default_factory=list)


def run_preflight(repo_root: Path, will_create_prs: bool) -> PreflightResult:
    """Preconditions: tk present, remote configured, clean tree, and
    (only when PR creation will run) an authenticated gh/glab. Never
    counted against the failure cap — this fails the whole run, not one ticket."""
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
