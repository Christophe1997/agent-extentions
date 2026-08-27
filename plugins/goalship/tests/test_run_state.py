"""Tests for the goalship run-state ledger.

Run from the repo root:
    python3 -m pytest plugins/goalship/tests/test_run_state.py -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Make the `scripts/` sibling modules importable without packaging gymnastics.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import preflight  # noqa: E402
import run_state  # noqa: E402


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("placeholder\n")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


class RunStateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self._tmp.name)
        _init_repo(self.repo_root)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestFreshAndResumedLedger(RunStateTestCase):
    def test_fresh_run_creates_new_ledger_with_zero_counters(self):
        state = run_state.load_run_state(self.repo_root, "run-fresh")
        self.assertEqual(state.run_id, "run-fresh")
        self.assertEqual(state.shipped_count, 0)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertEqual(state.claimed_ticket_ids, [])

    def test_resumed_run_reads_existing_ledger_and_preserves_counts(self):
        state = run_state.load_run_state(self.repo_root, "run-a")
        state.shipped_count = 4
        state.consecutive_failures = 1
        run_state.claim_ticket(state, "T-1")
        run_state.save_run_state(self.repo_root, state)

        resumed = run_state.load_run_state(self.repo_root, "run-a")
        self.assertEqual(resumed.shipped_count, 4)
        self.assertEqual(resumed.consecutive_failures, 1)
        self.assertEqual(resumed.claimed_ticket_ids, ["T-1"])


class TestFailureCounterResets(RunStateTestCase):
    def test_consecutive_failure_resets_to_zero_after_success(self):
        state = run_state.RunState(run_id="run-b", consecutive_failures=2)
        run_state.record_ship(state)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertEqual(state.shipped_count, 1)

    def test_consecutive_failure_does_not_reset_after_block(self):
        state = run_state.RunState(run_id="run-c", consecutive_failures=1)
        run_state.record_failure(state)
        self.assertEqual(state.consecutive_failures, 2)
        self.assertEqual(state.shipped_count, 0)


class TestCaps(RunStateTestCase):
    def test_caps_not_exceeded_under_both_thresholds(self):
        state = run_state.RunState(run_id="run-d", shipped_count=1, consecutive_failures=1)
        self.assertIsNone(run_state.caps_exceeded(state))

    def test_ship_cap_exceeded(self):
        state = run_state.RunState(run_id="run-e", shipped_count=run_state.SHIP_CAP)
        reason = run_state.caps_exceeded(state)
        self.assertIsNotNone(reason)
        self.assertIn(str(run_state.SHIP_CAP), reason)

    def test_failure_cap_exceeded(self):
        state = run_state.RunState(run_id="run-f", consecutive_failures=run_state.FAILURE_CAP)
        reason = run_state.caps_exceeded(state)
        self.assertIsNotNone(reason)
        self.assertIn(str(run_state.FAILURE_CAP), reason)


class TestConcurrentRunIsolation(RunStateTestCase):
    def test_two_run_ids_never_clobber_each_other(self):
        state_a = run_state.load_run_state(self.repo_root, "run-alpha")
        state_a.shipped_count = 3
        run_state.claim_ticket(state_a, "T-alpha")
        run_state.save_run_state(self.repo_root, state_a)

        state_b = run_state.load_run_state(self.repo_root, "run-beta")
        state_b.shipped_count = 7
        run_state.claim_ticket(state_b, "T-beta")
        run_state.save_run_state(self.repo_root, state_b)

        reloaded_a = run_state.load_run_state(self.repo_root, "run-alpha")
        reloaded_b = run_state.load_run_state(self.repo_root, "run-beta")

        self.assertEqual(reloaded_a.shipped_count, 3)
        self.assertEqual(reloaded_a.claimed_ticket_ids, ["T-alpha"])
        self.assertEqual(reloaded_b.shipped_count, 7)
        self.assertEqual(reloaded_b.claimed_ticket_ids, ["T-beta"])


class TestGoalAndTicketModePersist(RunStateTestCase):
    def test_fresh_state_has_no_goal_or_mode_or_terminal_state(self):
        state = run_state.load_run_state(self.repo_root, "run-h")
        self.assertEqual(state.goal, "")
        self.assertIsNone(state.ticket_mode)
        self.assertIsNone(state.terminal_state)
        self.assertIsNone(state.trunk_branch)

    def test_goal_and_ticket_mode_round_trip_through_save_and_load(self):
        state = run_state.load_run_state(self.repo_root, "run-i")
        state.goal = "ship the widget"
        state.ticket_mode = "commit"
        run_state.save_run_state(self.repo_root, state)

        resumed = run_state.load_run_state(self.repo_root, "run-i")
        self.assertEqual(resumed.goal, "ship the widget")
        self.assertEqual(resumed.ticket_mode, "commit")

    def test_trunk_branch_round_trips_through_save_and_load(self):
        state = run_state.load_run_state(self.repo_root, "run-trunk")
        state.trunk_branch = "develop"
        run_state.save_run_state(self.repo_root, state)

        resumed = run_state.load_run_state(self.repo_root, "run-trunk")
        self.assertEqual(resumed.trunk_branch, "develop")


class TestMarkTerminal(RunStateTestCase):
    def test_mark_terminal_sets_the_reason(self):
        state = run_state.RunState(run_id="run-j")
        run_state.mark_terminal(state, run_state.TERMINAL_EXHAUSTED)
        self.assertEqual(state.terminal_state, run_state.TERMINAL_EXHAUSTED)

    def test_mark_terminal_rejects_an_unknown_reason(self):
        state = run_state.RunState(run_id="run-k")
        with self.assertRaises(ValueError):
            run_state.mark_terminal(state, "not_a_real_reason")

    def test_mark_terminal_accepts_aborted_for_non_ticket_graph_stops(self):
        state = run_state.RunState(run_id="run-abort")
        run_state.mark_terminal(state, run_state.TERMINAL_ABORTED)
        self.assertEqual(state.terminal_state, run_state.TERMINAL_ABORTED)


class TestFindResumableRuns(RunStateTestCase):
    def test_no_ledger_dir_yet_returns_empty(self):
        self.assertEqual(run_state.find_resumable_runs(self.repo_root), [])

    def test_in_progress_run_is_resumable(self):
        state = run_state.load_run_state(self.repo_root, "run-l")
        state.goal = "ship the widget"
        state.ticket_mode = "branch"
        run_state.save_run_state(self.repo_root, state)

        candidates = run_state.find_resumable_runs(self.repo_root)
        self.assertEqual([s.run_id for s in candidates], ["run-l"])
        self.assertEqual(candidates[0].goal, "ship the widget")
        self.assertEqual(candidates[0].ticket_mode, "branch")

    def test_terminal_run_is_excluded(self):
        state = run_state.load_run_state(self.repo_root, "run-m")
        run_state.mark_terminal(state, run_state.TERMINAL_DEADLOCKED)
        run_state.save_run_state(self.repo_root, state)

        self.assertEqual(run_state.find_resumable_runs(self.repo_root), [])

    def test_mixed_runs_only_surfaces_the_unfinished_one(self):
        done = run_state.load_run_state(self.repo_root, "run-done")
        run_state.mark_terminal(done, run_state.TERMINAL_CAPPED)
        run_state.save_run_state(self.repo_root, done)

        live = run_state.load_run_state(self.repo_root, "run-live")
        run_state.save_run_state(self.repo_root, live)

        candidates = run_state.find_resumable_runs(self.repo_root)
        self.assertEqual([s.run_id for s in candidates], ["run-live"])

    def test_truncated_json_ledger_file_is_skipped_not_fatal(self):
        live = run_state.load_run_state(self.repo_root, "run-live")
        run_state.save_run_state(self.repo_root, live)
        ledger_dir = self.repo_root / run_state.LEDGER_DIR_NAME
        (ledger_dir / "corrupt.json").write_text("{not valid json")

        candidates = run_state.find_resumable_runs(self.repo_root)

        self.assertEqual([s.run_id for s in candidates], ["run-live"])

    def test_ledger_file_missing_run_id_is_skipped_not_fatal(self):
        live = run_state.load_run_state(self.repo_root, "run-live")
        run_state.save_run_state(self.repo_root, live)
        ledger_dir = self.repo_root / run_state.LEDGER_DIR_NAME
        (ledger_dir / "no-run-id.json").write_text('{"shipped_count": 1}')

        candidates = run_state.find_resumable_runs(self.repo_root)

        self.assertEqual([s.run_id for s in candidates], ["run-live"])


class TestLedgerExcludedFromDirtyCheck(RunStateTestCase):
    def test_writing_ledger_does_not_trip_dirty_tree_check(self):
        self.assertEqual(preflight.dirty_paths(self.repo_root), [])

        state = run_state.load_run_state(self.repo_root, "run-g")
        run_state.save_run_state(self.repo_root, state)

        self.assertEqual(preflight.dirty_paths(self.repo_root), [])

    def test_ensure_ledger_excluded_adds_entry_once(self):
        run_state.ensure_ledger_excluded(self.repo_root)
        run_state.ensure_ledger_excluded(self.repo_root)
        exclude_file = self.repo_root / ".git" / "info" / "exclude"
        contents = exclude_file.read_text()
        self.assertEqual(contents.count(run_state.LEDGER_DIR_NAME), 1)


if __name__ == "__main__":
    unittest.main()
