"""tk mechanics (note read/write, structured-note parsing) and loop-start
reconciliation — cross-checking every in-progress ticket against git/PR
state before the next `tk ready` pick.

`tk` auto-discovers `.tickets/` by walking up from cwd (same mechanism
git uses for `.git/`), so every wrapper below just runs with cwd=repo_root
rather than managing TICKETS_DIR itself.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import preflight
import run_state

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


def record_claim_note(
    repo_root: Path, ticket_id: str, branch: str,
    base: Optional[str] = None, claim_sha: Optional[str] = None,
) -> None:
    """Written at claim time, before implementation starts — the only
    record of a ticket's branch that survives a crash before any later note.
    `claim_sha`, when given, is that branch's tip at the moment of claim —
    the baseline commit_landed_since compares against to tell whether this
    ticket's own work has landed, not merely whether the branch has any
    commits past its base at all (which a shared branch always would,
    from earlier tickets)."""
    lines = [f"branch: {branch}"]
    if base:
        lines.append(f"base: {base}")
    if claim_sha:
        lines.append(f"claim_sha: {claim_sha}")
    tk_add_note(repo_root, ticket_id, "\n".join(lines))


def record_ship_note(repo_root: Path, ticket_id: str, branch: str, pr_url: str, sha: str) -> None:
    """On success, the closing note records branch, PR URL, and head SHA."""
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


def find_run_branch(repo_root: Path, claimed_ticket_ids: list) -> Optional[str]:
    """The shared branch a commit-mode run's already-claimed tickets are
    landing on, discovered from their own claim notes rather than a new
    ledger field — so a lost/corrupted ledger still leaves this
    recoverable. Returns the first claimed ticket's recorded `branch:`,
    or None if none is claimed yet (this ticket is the run's first) or
    none of them have a branch note yet."""
    for ticket_id in claimed_ticket_ids:
        branch = note_fields_for_ticket(repo_root, ticket_id).get("branch")
        if branch:
            return branch
    return None


def find_ticket_by_branch(repo_root: Path, branch: str) -> Optional[tuple]:
    """(ticket_id, note_fields) for the ticket whose branch note matches, or
    None. Returns the fields alongside the id so a caller that needs them
    (reconcile's stacked-base lookup) doesn't re-issue an identical `tk
    show` for the ticket it just found."""
    for ticket in tk_query(repo_root, "."):
        fields = note_fields_for_ticket(repo_root, ticket["id"])
        if fields.get("branch") == branch:
            return ticket["id"], fields
    return None


def pr_state(repo_root: Path, host_tool: Optional[str], pr_ref: str) -> Optional[str]:
    """"open" | "merged" | "closed", or None when the lookup itself failed
    (e.g. an expired credential) — kept distinct from a legitimately
    non-open PR so callers don't misreport "can't tell" as "not open"."""
    if host_tool == "gh":
        result = subprocess.run(
            ["gh", "pr", "view", pr_ref, "--json", "state", "-q", ".state"],
            cwd=repo_root, capture_output=True, text=True,
            timeout=run_state.HOST_TOOL_TIMEOUT_SECONDS,
        )
        raw = result.stdout.strip() if result.returncode == 0 else ""
    elif host_tool == "glab":
        result = subprocess.run(
            ["glab", "mr", "view", pr_ref, "-F", "json"],
            cwd=repo_root, capture_output=True, text=True,
            timeout=run_state.HOST_TOOL_TIMEOUT_SECONDS,
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


def find_open_pr_for_branch(repo_root: Path, host_tool: Optional[str], branch: str) -> Optional[str]:
    """The URL of an already-open PR/MR for `branch`, or None. Queried
    directly against the host rather than tracked in the run-state ledger —
    same ledger-independence reasoning as reconcile() itself, so a
    lost/corrupted ledger doesn't strand a commit-mode run's shared-PR
    discovery. Both hosts default to listing only open PRs/MRs; `gh` is
    given `--state open` explicitly anyway since that's the contract this
    function promises, not an assumption about gh's own default. `glab`
    has no equivalent `--state` flag at all (confirmed against `glab`
    1.106.0 on a live git.bilibili.co repo: `glab mr list --help` states
    "Defaults to open merge requests"; a merged MR was correctly excluded
    with no state flag passed) — its default is the whole contract there,
    not a redundant belt-and-suspenders flag.

    Unlike pr_state, this does not distinguish "no PR exists" from "the
    host query itself failed" — both return None. That's a deliberate,
    accepted collapse: a caller that gets None here and proceeds to
    create-pr on a branch that actually already has one fails loudly there
    instead (the host rejects a second open PR from the same head), which
    the existing failure-cap bookkeeping already counts and retries next
    cycle. A three-state return here would only protect against a failure
    mode that already fails safely one step later."""
    if host_tool == "gh":
        argv = ["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url"]
        url_key = "url"
    elif host_tool == "glab":
        argv = ["glab", "mr", "list", "--source-branch", branch, "-F", "json"]
        url_key = "web_url"
    else:
        return None

    result = subprocess.run(
        argv, cwd=repo_root, capture_output=True, text=True,
        timeout=run_state.HOST_TOOL_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return None
    try:
        prs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not prs:
        return None
    return prs[0].get(url_key)


@dataclass
class ReconciliationAction:
    ticket_id: str
    outcome: str
    detail: str = ""
    # For retarget_base_merged, the ticket's own `pr:` ref — carried
    # here so the skill can retarget it directly instead of re-parsing
    # `tk show` notes by hand.
    pr_ref: str = ""


@dataclass
class ReconciliationReport:
    actions: list = field(default_factory=list)
    auth_failure: Optional[str] = None


def _reconcile_stacked_base(
    repo_root: Path, host_tool: Optional[str], ticket_id: str, base: str, pr_ref: str,
) -> Optional[ReconciliationAction]:
    """A ticket's PR is open and stacked on `base` — check whether
    that base's own PR has since resolved out from under it. `pr_ref` is
    `ticket_id`'s own PR (not `base`'s) — carried onto the resulting action
    so a caller can retarget it without a second lookup."""
    found = find_ticket_by_branch(repo_root, base)
    base_fields = found[1] if found else {}
    base_pr = base_fields.get("pr")
    base_state = pr_state(repo_root, host_tool, base_pr) if base_pr else None
    if base_state == "merged":
        return ReconciliationAction(ticket_id, "retarget_base_merged", base, pr_ref=pr_ref)
    if base_state == "closed":
        tk_add_note(
            repo_root, ticket_id,
            f"Reconciliation: base {base} closed without merging; blocked.",
        )
        return ReconciliationAction(ticket_id, "blocked_stale_base", base)
    return None


def reconcile(repo_root: Path) -> ReconciliationReport:
    """Cross-check every in-progress ticket against git/PR state
    before the next `tk ready` pick.

    Always queries tk directly for the in-progress set — the durable
    source of truth for ticket status — rather than the run-state ledger,
    so "fall back to tk's own in-progress tickets when the ledger is
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
        host_tool = preflight._detect_host_tool()
        if host_tool is None or not preflight._host_tool_authenticated(host_tool):
            # A credential that keeps failing routes to a
            # preflight-class stop instead of retrying per ticket without limit.
            return ReconciliationReport(auth_failure=host_tool or "gh/glab")

    actions = []
    for ticket_id, fields in tickets_with_fields:
        pr_ref = fields.get("pr")
        branch = fields.get("branch")
        base = fields.get("base")
        sha = fields.get("sha")

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
            action = None
            if base:
                action = _reconcile_stacked_base(repo_root, host_tool, ticket_id, base, pr_ref)
            if action:
                actions.append(action)
            elif sha:
                # The PR is genuinely open (nothing stale to retarget
                # or block on) and the ship note (record_ship_note) has
                # already run — sha only ever appears alongside pr, so its
                # presence means the loop's own work here is done. A crash
                # between record_ship_note and cmd_ship's follow-up
                # tk_close is the only way a ticket reaches this shape, so
                # finish the close the crash interrupted rather than
                # leaving it stuck in_progress indefinitely.
                tk_close(repo_root, ticket_id)
                actions.append(ReconciliationAction(ticket_id, "closed_ship_note_orphaned", branch or "", pr_ref))
        else:
            actions.append(ReconciliationAction(ticket_id, "pr_state_unresolved", pr_ref))

    return ReconciliationReport(actions=actions)
