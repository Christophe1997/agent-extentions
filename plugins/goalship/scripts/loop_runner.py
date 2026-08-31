#!/usr/bin/env python3
"""CLI dispatcher for goalship's deterministic git/tk/gh mechanics and
durable run-state ledger. The skill runs and interprets the target repo's
gate commands itself — this script never wraps gate execution, so gate
output stays visible in the transcript.

Run standalone (`loop_runner.py <subcommand> ...`, see USAGE below) for
the CLI surface skills/goalship/references/execution-loop.md drives. The
logic itself lives in the sibling modules this dispatches to —
`run_state.py` (ledger persistence and caps), `preflight.py` (repo/remote/
host-tool preconditions), `reconciliation.py` (tk mechanics and loop-start
reconciliation), `branching.py` (branch/commit/PR operations) — each
importable directly (as the tests do) to use its functions without going
through the CLI.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import run_state
import preflight
import reconciliation
import branching


# ---------------------------------------------------------------------------
# CLI dispatcher — the skill's invocation surface. Each cmd_* function is a
# thin argv-to-function-call adapter; the logic itself lives in the
# sibling modules imported above, mirroring this repo's yapermission/a2a
# script convention.
# ---------------------------------------------------------------------------

USAGE = """Usage:
  loop_runner.py preflight <repo_root> <true|false> [trunk_branch]
  loop_runner.py reconcile <repo_root>
  loop_runner.py ledger <repo_root> [--run-id ID] [--claim TICKET_ID] [--ship] [--fail]
                        [--goal TEXT] [--ticket-mode branch|commit] [--trunk-branch NAME] [--terminal REASON]
  loop_runner.py resume-candidates <repo_root>
  loop_runner.py dirty <repo_root>
  loop_runner.py branch-name <repo_root> <type> <title>
  loop_runner.py resolve-base <repo_root> <ticket_id> <trunk_branch> [host_tool]
  loop_runner.py commit-landed <repo_root> <branch> <claim_sha>
  loop_runner.py run-branch <repo_root> [ticket_id ...]
  loop_runner.py find-pr <repo_root> <host_tool> <branch>
  loop_runner.py claim <repo_root> <ticket_id> <branch_name> <base_ref> <trunk_branch>
  loop_runner.py commit <repo_root> <message>
  loop_runner.py head-sha <repo_root> <branch>
  loop_runner.py push <repo_root> <branch_name>
  loop_runner.py create-pr <repo_root> <host_tool> <branch> <base> <title> <body>
  loop_runner.py retarget-pr <repo_root> <host_tool> <pr_ref> <new_base>
  loop_runner.py ship <repo_root> <ticket_id> <branch> <pr_url> <sha>
  loop_runner.py reset <repo_root> <base_branch>
"""


def _print_json(data) -> None:
    print(json.dumps(data))


def cmd_preflight(args: list) -> None:
    if len(args) < 2:
        print("error: usage: preflight <repo_root> <true|false> [trunk_branch]", file=sys.stderr)
        sys.exit(1)
    trunk_branch_override = args[2] if len(args) > 2 else None
    result = preflight.run_preflight(Path(args[0]), args[1].lower() == "true", trunk_branch_override)
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
    report = reconciliation.reconcile(Path(args[0]))
    _print_json({
        "actions": [
            {"ticket_id": a.ticket_id, "outcome": a.outcome, "detail": a.detail, "pr_ref": a.pr_ref}
            for a in report.actions
        ],
        "auth_failure": report.auth_failure,
    })


def cmd_ledger(args: list) -> None:
    if len(args) < 1:
        print(
            "error: usage: ledger <repo_root> [--run-id ID] [--claim TICKET_ID] [--ship] [--fail]\n"
            "                     [--goal TEXT] [--ticket-mode branch|commit] [--trunk-branch NAME] [--terminal REASON]",
            file=sys.stderr,
        )
        sys.exit(1)
    repo_root = Path(args[0])
    run_id = None
    claim_id = None
    ship = False
    fail = False
    goal = None
    ticket_mode = None
    trunk_branch = None
    terminal = None
    rest = args[1:]
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in ("--run-id", "--claim", "--goal", "--ticket-mode", "--trunk-branch", "--terminal"):
            if i + 1 >= len(rest):
                print(f"error: {tok} requires a value", file=sys.stderr)
                sys.exit(1)
            i += 1
            if tok == "--run-id":
                run_id = rest[i]
            elif tok == "--claim":
                claim_id = rest[i]
            elif tok == "--goal":
                goal = rest[i]
            elif tok == "--ticket-mode":
                ticket_mode = rest[i]
            elif tok == "--trunk-branch":
                trunk_branch = rest[i]
            else:
                terminal = rest[i]
        elif tok == "--ship":
            ship = True
        elif tok == "--fail":
            fail = True
        else:
            print(f"error: unknown ledger flag '{tok}'", file=sys.stderr)
            sys.exit(1)
        i += 1

    if ticket_mode is not None and ticket_mode not in run_state.TICKET_MODES:
        print(
            f"error: --ticket-mode must be one of {sorted(run_state.TICKET_MODES)}, got {ticket_mode!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    if terminal is not None and terminal not in run_state.TERMINAL_STATES:
        print(
            f"error: --terminal must be one of {sorted(run_state.TERMINAL_STATES)}, got {terminal!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    run_state.ensure_ledger_excluded(repo_root)
    state = run_state.load_run_state(repo_root, run_id or run_state.generate_run_id())
    if claim_id:
        run_state.claim_ticket(state, claim_id)
    if ship:
        run_state.record_ship(state)
    if fail:
        run_state.record_failure(state)
    if goal is not None:
        state.goal = goal
    if ticket_mode is not None:
        state.ticket_mode = ticket_mode
    if trunk_branch is not None:
        state.trunk_branch = trunk_branch
    if terminal is not None:
        run_state.mark_terminal(state, terminal)
    run_state.save_run_state(repo_root, state)

    data = state.to_dict()
    data["caps_exceeded"] = run_state.caps_exceeded(state)
    _print_json(data)


def cmd_resume_candidates(args: list) -> None:
    if len(args) < 1:
        print("error: usage: resume-candidates <repo_root>", file=sys.stderr)
        sys.exit(1)
    candidates = run_state.find_resumable_runs(Path(args[0]))
    _print_json([
        {
            "run_id": s.run_id,
            "goal": s.goal,
            "ticket_mode": s.ticket_mode,
            "shipped_count": s.shipped_count,
            "consecutive_failures": s.consecutive_failures,
            "claimed_ticket_ids": s.claimed_ticket_ids,
        }
        for s in candidates
    ])


def cmd_dirty(args: list) -> None:
    if len(args) < 1:
        print("error: usage: dirty <repo_root>", file=sys.stderr)
        sys.exit(1)
    _print_json(preflight.dirty_paths(Path(args[0])))


def cmd_branch_name(args: list) -> None:
    if len(args) < 3:
        print("error: usage: branch-name <repo_root> <type> <title>", file=sys.stderr)
        sys.exit(1)
    print(branching.branch_name_for_ticket(Path(args[0]), args[1], args[2]))


def cmd_resolve_base(args: list) -> None:
    if len(args) < 3:
        print("error: usage: resolve-base <repo_root> <ticket_id> <trunk_branch> [host_tool]", file=sys.stderr)
        sys.exit(1)
    host_tool = args[3] if len(args) > 3 else None
    print(branching.resolve_base_for_ticket(Path(args[0]), args[1], args[2], host_tool))


def cmd_commit_landed_since(args: list) -> None:
    if len(args) < 3:
        print("error: usage: commit-landed <repo_root> <branch> <claim_sha>", file=sys.stderr)
        sys.exit(1)
    print("yes" if branching.commit_landed_since(Path(args[0]), args[1], args[2]) else "no")


def cmd_run_branch(args: list) -> None:
    if len(args) < 1:
        print("error: usage: run-branch <repo_root> [ticket_id ...]", file=sys.stderr)
        sys.exit(1)
    branch = reconciliation.find_run_branch(Path(args[0]), args[1:])
    if branch:
        print(branch)


def cmd_find_pr(args: list) -> None:
    if len(args) < 3:
        print("error: usage: find-pr <repo_root> <host_tool> <branch>", file=sys.stderr)
        sys.exit(1)
    url = reconciliation.find_open_pr_for_branch(Path(args[0]), args[1], args[2])
    if url:
        print(url)


def cmd_claim(args: list) -> None:
    if len(args) < 5:
        print("error: usage: claim <repo_root> <ticket_id> <branch_name> <base_ref> <trunk_branch>", file=sys.stderr)
        sys.exit(1)
    repo_root, ticket_id, branch_name, base_ref, trunk_branch = Path(args[0]), args[1], args[2], args[3], args[4]
    if branching.local_branch_exists(repo_root, branch_name):
        # Crash recovery: a prior claim already created the branch but
        # crashed before writing the claim note. Retry from here instead
        # of failing on "branch already exists", checking the branch back
        # out so implementation resumes on it as create_branch would have
        # left it.
        subprocess.run(["git", "checkout", branch_name], cwd=repo_root, check=True, capture_output=True)
    else:
        branching.create_branch(repo_root, branch_name, base_ref)
    # Captured after checkout-or-create so it's correct on both paths: the
    # branch's actual current tip, whether that's a brand-new branch (tip
    # == base_ref) or a crash-recovery retry resuming an existing one.
    claim_sha = branching.head_sha(repo_root)
    reconciliation.record_claim_note(
        repo_root, ticket_id, branch_name,
        base=base_ref if base_ref != trunk_branch else None,
        claim_sha=claim_sha,
    )


def cmd_commit(args: list) -> None:
    if len(args) < 2:
        print("error: usage: commit <repo_root> <message>", file=sys.stderr)
        sys.exit(1)
    print(branching.commit_all(Path(args[0]), args[1]))


def cmd_head_sha(args: list) -> None:
    if len(args) < 2:
        print("error: usage: head-sha <repo_root> <branch>", file=sys.stderr)
        sys.exit(1)
    print(branching.head_sha(Path(args[0]), args[1]))


def cmd_push(args: list) -> None:
    if len(args) < 2:
        print("error: usage: push <repo_root> <branch_name>", file=sys.stderr)
        sys.exit(1)
    branching.push_branch(Path(args[0]), args[1])


def cmd_create_pr(args: list) -> None:
    if len(args) < 6:
        print("error: usage: create-pr <repo_root> <host_tool> <branch> <base> <title> <body>", file=sys.stderr)
        sys.exit(1)
    repo_root, host_tool, branch, base, title, body = args[0], args[1], args[2], args[3], args[4], args[5]
    print(branching.create_pull_request(Path(repo_root), host_tool, branch, base, title, body))


def cmd_retarget_pr(args: list) -> None:
    if len(args) < 4:
        print("error: usage: retarget-pr <repo_root> <host_tool> <pr_ref> <new_base>", file=sys.stderr)
        sys.exit(1)
    branching.retarget_pull_request(Path(args[0]), args[1], args[2], args[3])


def cmd_ship(args: list) -> None:
    if len(args) < 5:
        print("error: usage: ship <repo_root> <ticket_id> <branch> <pr_url> <sha>", file=sys.stderr)
        sys.exit(1)
    repo_root, ticket_id, branch, pr_url, sha = Path(args[0]), args[1], args[2], args[3], args[4]
    reconciliation.record_ship_note(repo_root, ticket_id, branch, pr_url, sha)
    reconciliation.tk_close(repo_root, ticket_id)


def cmd_reset(args: list) -> None:
    if len(args) < 2:
        print("error: usage: reset <repo_root> <base_branch>", file=sys.stderr)
        sys.exit(1)
    branching.reset_to_clean_base(Path(args[0]), args[1])


_COMMANDS = {
    "preflight": cmd_preflight,
    "reconcile": cmd_reconcile,
    "ledger": cmd_ledger,
    "resume-candidates": cmd_resume_candidates,
    "dirty": cmd_dirty,
    "branch-name": cmd_branch_name,
    "resolve-base": cmd_resolve_base,
    "commit-landed": cmd_commit_landed_since,
    "run-branch": cmd_run_branch,
    "find-pr": cmd_find_pr,
    "claim": cmd_claim,
    "commit": cmd_commit,
    "head-sha": cmd_head_sha,
    "push": cmd_push,
    "create-pr": cmd_create_pr,
    "retarget-pr": cmd_retarget_pr,
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
    except subprocess.TimeoutExpired as exc:
        cmd = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd)
        print(f"error: `{cmd}` timed out after {exc.timeout}s", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
