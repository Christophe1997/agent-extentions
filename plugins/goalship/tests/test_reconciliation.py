"""Tests for goalship's loop-start reconciliation pass.

Run from the repo root:
    python3 -m pytest plugins/goalship/tests/test_reconciliation.py -v
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import loop_runner as lr  # noqa: E402


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class ReconciliationTestCase(unittest.TestCase):
    """A repo_root that is both a git repo and a `tk` ticket store."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self._tmp.name)
        _run(["git", "init", "-q"], self.repo_root)
        _run(["git", "config", "user.email", "test@example.com"], self.repo_root)
        _run(["git", "config", "user.name", "Test"], self.repo_root)
        (self.repo_root / "README.md").write_text("placeholder\n")
        _run(["git", "add", "README.md"], self.repo_root)
        _run(["git", "commit", "-q", "-m", "init"], self.repo_root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _tk_create(self, title: str) -> str:
        result = subprocess.run(
            ["tk", "create", title, "-t", "task"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip().splitlines()[-1]

    def _tk_status(self, ticket_id: str) -> str:
        tickets = lr.tk_query(self.repo_root, f'select(.id=="{ticket_id}")')
        return tickets[0]["status"]


class TestNoOpAndLedgerIndependence(ReconciliationTestCase):
    def test_fresh_run_with_no_in_progress_tickets_is_noop(self):
        self._tk_create("Untouched open ticket")
        report = lr.reconcile(self.repo_root)
        self.assertEqual(report.actions, [])
        self.assertIsNone(report.auth_failure)

    def test_reconciliation_never_reads_the_run_state_ledger(self):
        # No ledger file exists anywhere under repo_root; reconcile() must
        # not require one — this is trivially satisfied because the
        # function queries tk directly, not the ledger.
        self.assertFalse((self.repo_root / lr.LEDGER_DIR_NAME).exists())
        ticket_id = self._tk_create("In progress, no notes yet")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)

        report = lr.reconcile(self.repo_root)

        self.assertFalse((self.repo_root / lr.LEDGER_DIR_NAME).exists())
        self.assertEqual(len(report.actions), 1)
        self.assertEqual(report.actions[0].outcome, "no_recoverable_state")


class TestMergedAndClosedOutcomes(ReconciliationTestCase):
    def test_merged_pr_closes_ticket_with_note(self):
        ticket_id = self._tk_create("Ships a merged PR")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, ticket_id, "feat/merged-one")
        lr.record_ship_note(self.repo_root, ticket_id, "feat/merged-one", "https://example.com/pr/1", "abc123")

        with mock.patch.object(lr, "pr_state", return_value="merged"):
            report = lr.reconcile(self.repo_root)

        self.assertEqual(len(report.actions), 1)
        self.assertEqual(report.actions[0].outcome, "closed_merged")
        self.assertEqual(self._tk_status(ticket_id), "closed")

    def test_closed_unmerged_pr_marks_failed_and_leaves_open(self):
        ticket_id = self._tk_create("PR closed without merging")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, ticket_id, "feat/abandoned")
        lr.record_ship_note(self.repo_root, ticket_id, "feat/abandoned", "https://example.com/pr/2", "def456")

        with mock.patch.object(lr, "pr_state", return_value="closed"):
            report = lr.reconcile(self.repo_root)

        self.assertEqual(len(report.actions), 1)
        self.assertEqual(report.actions[0].outcome, "failed_closed_unmerged")
        self.assertEqual(self._tk_status(ticket_id), "open")


class TestRetryAndCrashResume(ReconciliationTestCase):
    def test_pushed_branch_no_pr_yet_retries_instead_of_reimplementing(self):
        ticket_id = self._tk_create("Crashed before PR creation")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, ticket_id, "feat/crashed")

        with mock.patch.object(lr, "_detect_host_tool", return_value="gh"), \
             mock.patch.object(lr, "_host_tool_authenticated", return_value=True):
            report = lr.reconcile(self.repo_root)

        self.assertEqual(len(report.actions), 1)
        self.assertEqual(report.actions[0].outcome, "retry_pr_creation")
        self.assertEqual(report.actions[0].detail, "feat/crashed")
        self.assertEqual(self._tk_status(ticket_id), "in_progress")

    def test_crash_after_commit_and_push_keeps_the_pushed_commit(self):
        """Simulated crash-and-resume: killed after commit+push, before
        `tk close`. The pushed branch and its commit must survive
        reconciliation untouched — recovery is a retry signal, not a
        rewrite of git history."""
        ticket_id = self._tk_create("Crash after push")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)

        _run(["git", "checkout", "-b", "feat/crash-after-push"], self.repo_root)
        (self.repo_root / "shipped.txt").write_text("done\n")
        # Stage only the intended file, not `git add -A` (lr.commit_all) —
        # the test's own `.tickets/` dir is untracked on purpose here, and
        # sweeping it onto this branch would make it vanish from the
        # working tree on the checkout back below, which is a test-fixture
        # artifact unrelated to what this test verifies.
        _run(["git", "add", "shipped.txt"], self.repo_root)
        _run(["git", "commit", "-q", "-m", "feat: shipped work"], self.repo_root)
        sha = lr.head_sha(self.repo_root)
        _run(["git", "checkout", "-"], self.repo_root)
        lr.record_claim_note(self.repo_root, ticket_id, "feat/crash-after-push")

        with mock.patch.object(lr, "_detect_host_tool", return_value="gh"), \
             mock.patch.object(lr, "_host_tool_authenticated", return_value=True):
            report = lr.reconcile(self.repo_root)

        self.assertEqual(report.actions[0].outcome, "retry_pr_creation")
        branch_sha = subprocess.run(
            ["git", "rev-parse", "feat/crash-after-push"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(branch_sha, sha)


class TestStackedBaseOutcomes(ReconciliationTestCase):
    def _setup_stacked_pair(self):
        base_id = self._tk_create("Base ticket")
        subprocess.run(["tk", "start", base_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, base_id, "feat/base")
        lr.record_ship_note(self.repo_root, base_id, "feat/base", "https://example.com/pr/10", "aaa111")

        dep_id = self._tk_create("Stacked on base")
        subprocess.run(["tk", "start", dep_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, dep_id, "feat/stacked", base="feat/base")
        lr.record_ship_note(self.repo_root, dep_id, "feat/stacked", "https://example.com/pr/11", "bbb222")
        return base_id, dep_id

    def test_stacked_ticket_retargets_when_base_merged(self):
        base_id, dep_id = self._setup_stacked_pair()

        def fake_pr_state(_repo_root, _host_tool, pr_ref):
            return "merged" if pr_ref == "https://example.com/pr/10" else "open"

        with mock.patch.object(lr, "pr_state", side_effect=fake_pr_state):
            report = lr.reconcile(self.repo_root)

        dep_actions = [a for a in report.actions if a.ticket_id == dep_id]
        self.assertEqual(len(dep_actions), 1)
        self.assertEqual(dep_actions[0].outcome, "retarget_base_merged")
        self.assertEqual(dep_actions[0].detail, "feat/base")
        # #5: the ticket's own PR ref rides along on the action so the
        # skill can retarget it without re-parsing `tk show` notes by hand.
        self.assertEqual(dep_actions[0].pr_ref, "https://example.com/pr/11")

    def test_stacked_ticket_blocked_when_base_closed_unmerged(self):
        base_id, dep_id = self._setup_stacked_pair()

        def fake_pr_state(_repo_root, _host_tool, pr_ref):
            if pr_ref == "https://example.com/pr/10":
                return "closed"
            return "open"

        with mock.patch.object(lr, "pr_state", side_effect=fake_pr_state):
            report = lr.reconcile(self.repo_root)

        dep_actions = [a for a in report.actions if a.ticket_id == dep_id]
        self.assertEqual(len(dep_actions), 1)
        self.assertEqual(dep_actions[0].outcome, "blocked_stale_base")
        self.assertEqual(self._tk_status(dep_id), "in_progress")


class TestAuthFailureRoutesToPreflightClassStop(ReconciliationTestCase):
    def test_unauthenticated_host_tool_stops_without_per_ticket_retries(self):
        ticket_id = self._tk_create("Needs a PR state check")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, ticket_id, "feat/needs-auth")
        lr.record_ship_note(self.repo_root, ticket_id, "feat/needs-auth", "https://example.com/pr/9", "ccc333")

        with mock.patch.object(lr, "_detect_host_tool", return_value="gh"), \
             mock.patch.object(lr, "_host_tool_authenticated", return_value=False):
            report = lr.reconcile(self.repo_root)

        self.assertEqual(report.auth_failure, "gh")
        self.assertEqual(report.actions, [])


class TestReconcileCommandJson(unittest.TestCase):
    """#5: cmd_reconcile's JSON serialization must carry the new pr_ref
    field the doc now reads directly, instead of only asserting it on the
    ReconciliationAction dataclass."""

    def test_serializes_pr_ref_alongside_outcome_and_detail(self):
        fake_report = lr.ReconciliationReport(
            actions=[
                lr.ReconciliationAction(
                    ticket_id="T-1", outcome="retarget_base_merged",
                    detail="feat/base", pr_ref="https://example.com/pr/11",
                ),
            ],
        )
        stdout = io.StringIO()
        with mock.patch.object(lr, "reconcile", return_value=fake_report), \
             contextlib.redirect_stdout(stdout):
            lr.cmd_reconcile(["/repo"])

        data = json.loads(stdout.getvalue())
        self.assertEqual(
            data["actions"],
            [{
                "ticket_id": "T-1", "outcome": "retarget_base_merged",
                "detail": "feat/base", "pr_ref": "https://example.com/pr/11",
            }],
        )


class TestShipNoteOrphanedOutcome(ReconciliationTestCase):
    """#6: cmd_ship writes the ship note (record_ship_note, setting pr:/sha:)
    then calls tk_close as a separate effect. A crash between them leaves a
    ticket in_progress with a complete ship note and an open PR that
    reconcile()'s plain `state == "open"` handling takes no action on —
    it sits stuck until the PR happens to externally merge or close."""

    def test_ship_note_written_but_not_closed_gets_closed_by_reconcile(self):
        ticket_id = self._tk_create("Crashed between ship note and tk close")
        subprocess.run(["tk", "start", ticket_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, ticket_id, "feat/orphaned-ship")
        lr.record_ship_note(self.repo_root, ticket_id, "feat/orphaned-ship", "https://example.com/pr/99", "sha999")
        # No tk_close call here — simulates the crash between
        # record_ship_note and tk_close inside cmd_ship. The PR itself is
        # genuinely still open (under review) — closed_merged and
        # failed_closed_unmerged already handle the merged/closed-unmerged
        # cases via the normal pr_state dispatch; this covers the
        # remaining "still open, nothing else to do" gap.
        self.assertEqual(self._tk_status(ticket_id), "in_progress")

        with mock.patch.object(lr, "pr_state", return_value="open"):
            report = lr.reconcile(self.repo_root)

        self.assertEqual(len(report.actions), 1)
        self.assertEqual(report.actions[0].outcome, "closed_ship_note_orphaned")
        self.assertEqual(report.actions[0].ticket_id, ticket_id)
        self.assertEqual(report.actions[0].detail, "feat/orphaned-ship")
        self.assertEqual(report.actions[0].pr_ref, "https://example.com/pr/99")
        self.assertEqual(self._tk_status(ticket_id), "closed")

    def test_stacked_ship_note_orphaned_when_base_pr_also_still_open(self):
        # A stacked ticket whose own PR is open and whose base's PR is
        # ALSO still open (nothing for _reconcile_stacked_base to retarget
        # or block on) must still fall through to the same close — proves
        # this outcome isn't gated behind "no base field at all".
        base_id = self._tk_create("Base ticket, still open")
        subprocess.run(["tk", "start", base_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, base_id, "feat/base-open")
        lr.record_ship_note(self.repo_root, base_id, "feat/base-open", "https://example.com/pr/20", "shaBase")

        dep_id = self._tk_create("Stacked, crashed before close")
        subprocess.run(["tk", "start", dep_id], cwd=self.repo_root, check=True, capture_output=True)
        lr.record_claim_note(self.repo_root, dep_id, "feat/stacked-open", base="feat/base-open")
        lr.record_ship_note(self.repo_root, dep_id, "feat/stacked-open", "https://example.com/pr/21", "shaDep")

        with mock.patch.object(lr, "pr_state", return_value="open"):
            report = lr.reconcile(self.repo_root)

        dep_actions = [a for a in report.actions if a.ticket_id == dep_id]
        self.assertEqual(len(dep_actions), 1)
        self.assertEqual(dep_actions[0].outcome, "closed_ship_note_orphaned")
        self.assertEqual(self._tk_status(dep_id), "closed")


if __name__ == "__main__":
    unittest.main()
