"""Tests for loop_runner.py's CLI dispatcher — the invocation surface the
goalship skill actually shells out to. Covers the dispatcher's own
argv contract and the JSON shape of the three structured commands the skill
parses (preflight, reconcile, ledger); every other subcommand is a
one-line delegation to a function already covered by the other test files,
so re-testing it here would just be re-testing git/tk through a subprocess.

Run from the repo root:
    python3 -m pytest plugins/goalship/tests/test_cli.py -v
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
_SCRIPT_PATH = _SCRIPTS / "loop_runner.py"
sys.path.insert(0, str(_SCRIPTS))
import loop_runner as lr  # noqa: E402


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), *args],
        capture_output=True, text=True,
    )


class TestDispatcherContract(unittest.TestCase):
    def test_no_subcommand_prints_usage_and_exits_1(self):
        result = _cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage", result.stderr)

    def test_unknown_subcommand_exits_1(self):
        result = _cli("frobnicate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown command", result.stderr)

    def test_missing_args_exits_1_with_usage(self):
        result = _cli("preflight")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: preflight", result.stderr)

    def test_retarget_pr_missing_args_exits_1_with_usage(self):
        result = _cli("retarget-pr")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: retarget-pr", result.stderr)

    def test_branch_has_commits_missing_args_exits_1_with_usage(self):
        result = _cli("branch-has-commits")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: branch-has-commits", result.stderr)

    def test_head_sha_missing_args_exits_1_with_usage(self):
        result = _cli("head-sha")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: head-sha", result.stderr)

    def test_git_failure_reports_stderr_and_exits_1_instead_of_a_traceback(self):
        result = _cli("commit", "/nonexistent-repo-path-xyz", "feat: nothing")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)


class TestTimeoutHandling(unittest.TestCase):
    """#1: gh/glab calls carry an explicit timeout so a hung host tool
    can't block an unattended loop forever; main() must report the
    resulting subprocess.TimeoutExpired as a clean CLI error, not a
    traceback — mirrors TestDispatcherContract's CalledProcessError test,
    but exercised in-process (via lr.main()) since a real hang isn't
    something a fast test can trigger through a spawned subprocess."""

    def test_host_tool_timeout_reports_clean_error_and_exits_1_instead_of_a_traceback(self):
        argv = [
            "loop_runner.py", "create-pr", "/repo", "gh",
            "feat/x", "main", "title", "body",
        ]
        timeout_exc = subprocess.TimeoutExpired(cmd=["gh", "pr", "create"], timeout=30)
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(lr.subprocess, "run", side_effect=timeout_exc), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as cm:
                lr.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertIn("error:", stderr.getvalue())


class TestRuntimeErrorHandling(unittest.TestCase):
    """#2: resolve_base_for_ticket raises RuntimeError when a dependency's
    pr_state() lookup fails (see test_branching.py's TestResolveBaseForTicket
    for that case) — main() must surface it as a clean CLI error too."""

    def test_runtime_error_reports_clean_message_and_exits_1_instead_of_a_traceback(self):
        argv = ["loop_runner.py", "resolve-base", "/repo", "T-1", "main", "gh"]
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(lr, "resolve_base_for_ticket", side_effect=RuntimeError("boom")), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as cm:
                lr.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertIn("error: boom", stderr.getvalue())


class CliRepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.bare_dir = root / "origin.git"
        self.repo_root = root / "work"
        self.repo_root.mkdir()

        _run(["git", "init", "-q", "--bare", str(self.bare_dir)], root)
        _run(["git", "init", "-q"], self.repo_root)
        _run(["git", "config", "user.email", "test@example.com"], self.repo_root)
        _run(["git", "config", "user.name", "Test"], self.repo_root)
        (self.repo_root / "README.md").write_text("placeholder\n")
        _run(["git", "add", "README.md"], self.repo_root)
        _run(["git", "commit", "-q", "-m", "init"], self.repo_root)
        _run(["git", "branch", "-m", "main"], self.repo_root)
        _run(["git", "remote", "add", "origin", str(self.bare_dir)], self.repo_root)
        _run(["git", "push", "-q", "-u", "origin", "main"], self.repo_root)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestPreflightCommand(CliRepoTestCase):
    def test_prints_the_preflight_json_shape(self):
        result = _cli("preflight", str(self.repo_root), "false")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(
            set(data.keys()),
            {"ok", "remote_url", "trunk_branch", "host_tool", "failures"},
        )
        self.assertTrue(data["ok"], data["failures"])
        self.assertEqual(data["trunk_branch"], "main")


class TestReconcileCommand(CliRepoTestCase):
    def test_prints_the_reconciliation_json_shape_for_a_clean_repo(self):
        # reconcile() always runs after decomposition has created at least
        # one ticket (F1's flow order) — `.tickets/` existing is a
        # precondition, not something reconcile() itself must handle.
        subprocess.run(
            ["tk", "create", "Untouched open ticket", "-t", "task"],
            cwd=self.repo_root, check=True, capture_output=True,
        )
        result = _cli("reconcile", str(self.repo_root))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data, {"actions": [], "auth_failure": None})


class TestBranchHasCommitsCommand(CliRepoTestCase):
    """The doc branches on these exact `yes`/`no` literals (retry_pr_creation
    crash recovery), so the wrapper's rendering — not just the underlying
    bool — is part of the CLI contract."""

    def test_prints_no_for_a_branch_with_no_commits_past_base(self):
        _run(["git", "checkout", "-q", "-b", "feat/empty"], self.repo_root)
        result = _cli("branch-has-commits", str(self.repo_root), "main", "feat/empty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "no")

    def test_prints_yes_once_the_branch_has_a_commit(self):
        _run(["git", "checkout", "-q", "-b", "feat/has-commit"], self.repo_root)
        (self.repo_root / "file.txt").write_text("x\n")
        _run(["git", "add", "file.txt"], self.repo_root)
        _run(["git", "commit", "-q", "-m", "feat: add file"], self.repo_root)
        result = _cli("branch-has-commits", str(self.repo_root), "main", "feat/has-commit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "yes")


class TestHeadShaCommand(CliRepoTestCase):
    def test_prints_the_sha_of_an_arbitrary_ref_not_just_head(self):
        _run(["git", "checkout", "-q", "-b", "feat/other"], self.repo_root)
        (self.repo_root / "file.txt").write_text("x\n")
        _run(["git", "add", "file.txt"], self.repo_root)
        _run(["git", "commit", "-q", "-m", "feat: add file"], self.repo_root)
        expected = subprocess.run(
            ["git", "rev-parse", "feat/other"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        _run(["git", "checkout", "-q", "main"], self.repo_root)

        result = _cli("head-sha", str(self.repo_root), "feat/other")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)


class TestLedgerCommand(CliRepoTestCase):
    def test_fresh_call_without_run_id_generates_and_persists_one(self):
        result = _cli("ledger", str(self.repo_root))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["run_id"])
        self.assertEqual(data["shipped_count"], 0)
        self.assertIsNone(data["caps_exceeded"])

        state = lr.load_run_state(self.repo_root, data["run_id"])
        self.assertEqual(state.run_id, data["run_id"])

    def test_claim_ship_and_fail_flags_mutate_and_persist(self):
        first = json.loads(_cli("ledger", str(self.repo_root)).stdout)
        run_id = first["run_id"]

        result = _cli(
            "ledger", str(self.repo_root),
            "--run-id", run_id, "--claim", "T-1", "--ship",
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["claimed_ticket_ids"], ["T-1"])
        self.assertEqual(data["shipped_count"], 1)
        self.assertEqual(data["consecutive_failures"], 0)

        result = _cli("ledger", str(self.repo_root), "--run-id", run_id, "--fail")
        data = json.loads(result.stdout)
        self.assertEqual(data["consecutive_failures"], 1)

    def test_caps_exceeded_surfaces_the_reason_string(self):
        run_id = json.loads(_cli("ledger", str(self.repo_root)).stdout)["run_id"]
        data = {}
        for _ in range(lr.FAILURE_CAP):
            data = json.loads(
                _cli("ledger", str(self.repo_root), "--run-id", run_id, "--fail").stdout
            )
        self.assertIn("consecutive-failure cap", data["caps_exceeded"])


if __name__ == "__main__":
    unittest.main()
