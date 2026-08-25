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

# Make `scripts/loop_runner.py` importable without packaging gymnastics.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import loop_runner as lr  # noqa: E402


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
        state = lr.load_run_state(self.repo_root, "run-fresh")
        self.assertEqual(state.run_id, "run-fresh")
        self.assertEqual(state.shipped_count, 0)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertEqual(state.claimed_ticket_ids, [])

    def test_resumed_run_reads_existing_ledger_and_preserves_counts(self):
        state = lr.load_run_state(self.repo_root, "run-a")
        state.shipped_count = 4
        state.consecutive_failures = 1
        lr.claim_ticket(state, "T-1")
        lr.save_run_state(self.repo_root, state)

        resumed = lr.load_run_state(self.repo_root, "run-a")
        self.assertEqual(resumed.shipped_count, 4)
        self.assertEqual(resumed.consecutive_failures, 1)
        self.assertEqual(resumed.claimed_ticket_ids, ["T-1"])


class TestFailureCounterResets(RunStateTestCase):
    def test_consecutive_failure_resets_to_zero_after_success(self):
        state = lr.RunState(run_id="run-b", consecutive_failures=2)
        lr.record_ship(state)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertEqual(state.shipped_count, 1)

    def test_consecutive_failure_does_not_reset_after_block(self):
        state = lr.RunState(run_id="run-c", consecutive_failures=1)
        lr.record_failure(state)
        self.assertEqual(state.consecutive_failures, 2)
        self.assertEqual(state.shipped_count, 0)


class TestCaps(RunStateTestCase):
    def test_caps_not_exceeded_under_both_thresholds(self):
        state = lr.RunState(run_id="run-d", shipped_count=1, consecutive_failures=1)
        self.assertIsNone(lr.caps_exceeded(state))

    def test_ship_cap_exceeded(self):
        state = lr.RunState(run_id="run-e", shipped_count=lr.SHIP_CAP)
        reason = lr.caps_exceeded(state)
        self.assertIsNotNone(reason)
        self.assertIn(str(lr.SHIP_CAP), reason)

    def test_failure_cap_exceeded(self):
        state = lr.RunState(run_id="run-f", consecutive_failures=lr.FAILURE_CAP)
        reason = lr.caps_exceeded(state)
        self.assertIsNotNone(reason)
        self.assertIn(str(lr.FAILURE_CAP), reason)


class TestConcurrentRunIsolation(RunStateTestCase):
    def test_two_run_ids_never_clobber_each_other(self):
        state_a = lr.load_run_state(self.repo_root, "run-alpha")
        state_a.shipped_count = 3
        lr.claim_ticket(state_a, "T-alpha")
        lr.save_run_state(self.repo_root, state_a)

        state_b = lr.load_run_state(self.repo_root, "run-beta")
        state_b.shipped_count = 7
        lr.claim_ticket(state_b, "T-beta")
        lr.save_run_state(self.repo_root, state_b)

        reloaded_a = lr.load_run_state(self.repo_root, "run-alpha")
        reloaded_b = lr.load_run_state(self.repo_root, "run-beta")

        self.assertEqual(reloaded_a.shipped_count, 3)
        self.assertEqual(reloaded_a.claimed_ticket_ids, ["T-alpha"])
        self.assertEqual(reloaded_b.shipped_count, 7)
        self.assertEqual(reloaded_b.claimed_ticket_ids, ["T-beta"])


class TestLedgerExcludedFromDirtyCheck(RunStateTestCase):
    def test_writing_ledger_does_not_trip_dirty_tree_check(self):
        self.assertEqual(lr.dirty_paths(self.repo_root), [])

        state = lr.load_run_state(self.repo_root, "run-g")
        lr.save_run_state(self.repo_root, state)

        self.assertEqual(lr.dirty_paths(self.repo_root), [])

    def test_ensure_ledger_excluded_adds_entry_once(self):
        lr.ensure_ledger_excluded(self.repo_root)
        lr.ensure_ledger_excluded(self.repo_root)
        exclude_file = self.repo_root / ".git" / "info" / "exclude"
        contents = exclude_file.read_text()
        self.assertEqual(contents.count(lr.LEDGER_DIR_NAME), 1)


if __name__ == "__main__":
    unittest.main()
