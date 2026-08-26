"""goalship's durable run-state ledger: persistence, caps, and the
git-exclude bookkeeping that keeps it out of the target repo's dirty-tree
checks. Also home to the fixed v1 tunables (caps, host-tool timeout,
this script's own state-dir names) every other module in this split
depends on — the base of the dependency chain, itself dependent on nothing
else here.
"""
from __future__ import annotations

import dataclasses
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Fixed v1 caps, not user-configurable, reset per invocation (not persisted).
SHIP_CAP = 10
FAILURE_CAP = 3

# Every gh/glab call this script makes is a simple auth-status/PR-create/
# PR-view/PR-edit round trip, not a long-running operation — an unattended,
# self-pacing loop has no one to notice a hang, so each call gets a
# watchdog rather than blocking forever on a stalled host or an
# interactive credential prompt.
HOST_TOOL_TIMEOUT_SECONDS = 30

# The ledger lives inside the target repo's own working tree, excluded
# from git via .git/info/exclude rather than relying on the repo's .gitignore.
LEDGER_DIR_NAME = ".goalship"

# The four terminal states execution-loop.md's cycle can end on. Persisted
# on the ledger so a cold re-invocation can tell a finished run from one
# merely paused mid-cycle (find_resumable_runs, below) without replaying
# tk/git state to work it out.
TERMINAL_EXHAUSTED = "exhausted"
TERMINAL_DEADLOCKED = "deadlocked"
TERMINAL_CAPPED = "capped"
TERMINAL_USER_STOP = "user_stop"
# Preflight/reconcile-auth/dirty-tree stops: none of these can make forward
# progress on a bare re-invocation without a human fixing the underlying
# problem first, so they're terminal too — just not one of the four
# ticket-graph outcomes above.
TERMINAL_ABORTED = "aborted"
TERMINAL_STATES = frozenset(
    {
        TERMINAL_EXHAUSTED,
        TERMINAL_DEADLOCKED,
        TERMINAL_CAPPED,
        TERMINAL_USER_STOP,
        TERMINAL_ABORTED,
    }
)

# execution-loop.md's two shipping modes (Shipping mode section) — the only
# valid values for RunState.ticket_mode.
TICKET_MODES = frozenset({"branch", "commit"})

# tk's own state directory. Excluded from this tool's dirty-tree check and
# commit staging for the same reason as LEDGER_DIR_NAME: `tk start`/`tk
# add-note` mutate it as a routine side effect of running this very loop,
# unrelated to a ticket's implementation diff. Whether the target repo
# tracks .tickets/ at all is that repo's own decision — this only
# keeps the loop's own commits and clean-tree checks from reacting to it.
TICKETS_DIR_NAME = ".tickets"


@dataclass
class RunState:
    run_id: str
    shipped_count: int = 0
    consecutive_failures: int = 0
    claimed_ticket_ids: list = field(default_factory=list)
    goal: str = ""
    ticket_mode: Optional[str] = None
    terminal_state: Optional[str] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunState":
        return cls(
            run_id=data["run_id"],
            shipped_count=data.get("shipped_count", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            claimed_ticket_ids=list(data.get("claimed_ticket_ids", [])),
            goal=data.get("goal", ""),
            ticket_mode=data.get("ticket_mode"),
            terminal_state=data.get("terminal_state"),
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
    that class of bug twice before landing on per-partition files.
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
    """A successful ship resets the consecutive-failure count."""
    state.shipped_count += 1
    state.consecutive_failures = 0


def record_failure(state: RunState) -> None:
    """A gate failure or a block both count toward the consecutive-failure cap."""
    state.consecutive_failures += 1


def claim_ticket(state: RunState, ticket_id: str) -> None:
    if ticket_id not in state.claimed_ticket_ids:
        state.claimed_ticket_ids.append(ticket_id)


def caps_exceeded(state: RunState) -> Optional[str]:
    """None when under both caps; otherwise the human-readable reason to stop."""
    if state.shipped_count >= SHIP_CAP:
        return f"ship cap reached ({SHIP_CAP} tickets shipped this run)"
    if state.consecutive_failures >= FAILURE_CAP:
        return f"consecutive-failure cap reached ({FAILURE_CAP} failures in a row)"
    return None


def mark_terminal(state: RunState, reason: str) -> None:
    """Record why this run stopped, so find_resumable_runs can tell a
    finished run from one merely paused mid-cycle."""
    if reason not in TERMINAL_STATES:
        raise ValueError(f"unknown terminal reason: {reason!r}")
    state.terminal_state = reason


def find_resumable_runs(repo_root: Path) -> list:
    """Every run under this repo's ledger dir that hasn't reached a
    terminal state yet.

    A cold re-invocation (no ScheduleWakeup on this harness, or a session
    that died before a scheduled wakeup fired) has no run_id to resume
    with — the wakeup prompt that would normally carry one forward never
    ran. Scanning the ledger dir instead of relying on a single well-known
    pointer file preserves resolve_ledger_path's one-file-per-run_id
    invariant: concurrent runs still never contend for the same inode.
    """
    ledger_dir = Path(repo_root) / LEDGER_DIR_NAME
    if not ledger_dir.exists():
        return []
    states = [
        RunState.from_dict(json.loads(path.read_text()))
        for path in sorted(ledger_dir.glob("*.json"))
    ]
    return [state for state in states if state.terminal_state is None]


def ensure_ledger_excluded(repo_root: Path) -> None:
    """Add the ledger dir to .git/info/exclude if it isn't already there."""
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
