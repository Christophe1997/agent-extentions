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
import branching  # noqa: E402
import reconciliation  # noqa: E402
import run_state  # noqa: E402


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

    def test_head_sha_missing_args_exits_1_with_usage(self):
        result = _cli("head-sha")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: head-sha", result.stderr)

    def test_commit_landed_missing_args_exits_1_with_usage(self):
        result = _cli("commit-landed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: commit-landed", result.stderr)

    def test_run_branch_missing_args_exits_1_with_usage(self):
        result = _cli("run-branch")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: run-branch", result.stderr)

    def test_find_pr_missing_args_exits_1_with_usage(self):
        result = _cli("find-pr")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage: find-pr", result.stderr)

    def test_git_failure_reports_stderr_and_exits_1_instead_of_a_traceback(self):
        result = _cli("commit", "/nonexistent-repo-path-xyz", "feat: nothing")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)


class TestTimeoutHandling(unittest.TestCase):
    """gh/glab calls carry an explicit timeout so a hung host tool
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
    """resolve_base_for_ticket raises RuntimeError when a dependency's
    pr_state() lookup fails (see test_branching.py's TestResolveBaseForTicket
    for that case) — main() must surface it as a clean CLI error too."""

    def test_runtime_error_reports_clean_message_and_exits_1_instead_of_a_traceback(self):
        argv = ["loop_runner.py", "resolve-base", "/repo", "T-1", "main", "gh"]
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(branching, "resolve_base_for_ticket", side_effect=RuntimeError("boom")), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as cm:
                lr.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertIn("error: boom", stderr.getvalue())


class TestFindPrCommand(unittest.TestCase):
    """find-pr's dispatcher output, exercised in-process (like
    TestTimeoutHandling) since the underlying gh/glab call can't be mocked
    through a spawned subprocess."""

    def test_prints_the_url_when_an_open_pr_exists(self):
        argv = ["loop_runner.py", "find-pr", "/repo", "gh", "feat/shared-goal"]
        fake_result = mock.Mock(returncode=0, stdout='[{"url": "https://github.com/o/r/pull/9"}]')
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(lr.subprocess, "run", return_value=fake_result), \
             contextlib.redirect_stdout(stdout):
            lr.main()
        self.assertEqual(stdout.getvalue().strip(), "https://github.com/o/r/pull/9")

    def test_prints_nothing_when_no_open_pr(self):
        argv = ["loop_runner.py", "find-pr", "/repo", "gh", "feat/x"]
        fake_result = mock.Mock(returncode=0, stdout="[]")
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(lr.subprocess, "run", return_value=fake_result), \
             contextlib.redirect_stdout(stdout):
            lr.main()
        self.assertEqual(stdout.getvalue().strip(), "")


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

    def test_trunk_branch_override_argument_is_forwarded_and_reflected(self):
        _run(["git", "checkout", "-q", "-b", "develop"], self.repo_root)
        _run(["git", "checkout", "-q", "main"], self.repo_root)
        result = _cli("preflight", str(self.repo_root), "false", "develop")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["ok"], data["failures"])
        self.assertEqual(data["trunk_branch"], "develop")


class TestRunBranchCommand(CliRepoTestCase):
    def test_prints_nothing_when_no_ticket_ids_given(self):
        result = _cli("run-branch", str(self.repo_root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_prints_the_branch_a_claimed_ticket_already_carries(self):
        create = subprocess.run(
            ["tk", "create", "Claimed and branched", "-t", "task"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        )
        ticket_id = create.stdout.strip().splitlines()[-1]
        reconciliation.record_claim_note(self.repo_root, ticket_id, "feat/shared-goal")

        result = _cli("run-branch", str(self.repo_root), ticket_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "feat/shared-goal")


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


class TestCommitLandedCommand(CliRepoTestCase):
    """The doc branches on these exact `yes`/`no` literals (retry_pr_creation
    crash recovery), so the wrapper's rendering — not just the underlying
    bool — is part of the CLI contract. Driven through the CLI dispatcher,
    not the Python function directly, so the wrapper's own argv/print
    plumbing is covered too."""

    def test_prints_no_immediately_after_claim_with_no_new_commit(self):
        _run(["git", "checkout", "-q", "-b", "feat/x"], self.repo_root)
        claim_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        result = _cli("commit-landed", str(self.repo_root), "feat/x", claim_sha)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "no")

    def test_prints_yes_once_a_commit_lands(self):
        _run(["git", "checkout", "-q", "-b", "feat/y"], self.repo_root)
        claim_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        (self.repo_root / "file.txt").write_text("x\n")
        _run(["git", "add", "file.txt"], self.repo_root)
        _run(["git", "commit", "-q", "-m", "feat: add file"], self.repo_root)
        result = _cli("commit-landed", str(self.repo_root), "feat/y", claim_sha)
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

        state = run_state.load_run_state(self.repo_root, data["run_id"])
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
        for _ in range(run_state.FAILURE_CAP):
            data = json.loads(
                _cli("ledger", str(self.repo_root), "--run-id", run_id, "--fail").stdout
            )
        self.assertIn("consecutive-failure cap", data["caps_exceeded"])

    def test_goal_and_ticket_mode_persist_and_round_trip(self):
        result = _cli(
            "ledger", str(self.repo_root),
            "--goal", "ship the widget", "--ticket-mode", "commit",
        )
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["goal"], "ship the widget")
        self.assertEqual(data["ticket_mode"], "commit")

        again = json.loads(_cli("ledger", str(self.repo_root), "--run-id", data["run_id"]).stdout)
        self.assertEqual(again["goal"], "ship the widget")
        self.assertEqual(again["ticket_mode"], "commit")

    def test_invalid_ticket_mode_exits_1(self):
        result = _cli("ledger", str(self.repo_root), "--ticket-mode", "sideways")
        self.assertEqual(result.returncode, 1)
        self.assertIn("sideways", result.stderr)

    def test_trunk_branch_persists_and_carries_forward_when_omitted(self):
        result = _cli("ledger", str(self.repo_root), "--trunk-branch", "develop")
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["trunk_branch"], "develop")

        again = json.loads(_cli("ledger", str(self.repo_root), "--run-id", data["run_id"]).stdout)
        self.assertEqual(again["trunk_branch"], "develop")

    def test_terminal_flag_persists_and_invalid_reason_exits_1(self):
        run_id = json.loads(_cli("ledger", str(self.repo_root)).stdout)["run_id"]
        result = _cli("ledger", str(self.repo_root), "--run-id", run_id, "--terminal", "exhausted")
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["terminal_state"], "exhausted")

        bad = _cli("ledger", str(self.repo_root), "--run-id", run_id, "--terminal", "on_fire")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("terminal", bad.stderr)


class TestResumeCandidatesCommand(CliRepoTestCase):
    def test_empty_when_no_ledger_dir_yet(self):
        result = _cli("resume-candidates", str(self.repo_root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_lists_an_in_progress_run_with_goal_and_mode(self):
        _cli("ledger", str(self.repo_root), "--goal", "ship the widget", "--ticket-mode", "branch")

        result = _cli("resume-candidates", str(self.repo_root))
        data = json.loads(result.stdout)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["goal"], "ship the widget")
        self.assertEqual(data[0]["ticket_mode"], "branch")

    def test_excludes_a_run_marked_terminal(self):
        run_id = json.loads(_cli("ledger", str(self.repo_root)).stdout)["run_id"]
        _cli("ledger", str(self.repo_root), "--run-id", run_id, "--terminal", "deadlocked")

        result = _cli("resume-candidates", str(self.repo_root))
        self.assertEqual(json.loads(result.stdout), [])

    def test_corrupt_ledger_file_does_not_crash_the_scan(self):
        data = json.loads(_cli("ledger", str(self.repo_root), "--goal", "ship it", "--ticket-mode", "branch").stdout)
        ledger_dir = self.repo_root / ".goalship"
        (ledger_dir / "corrupt.json").write_text("{not valid json")

        result = _cli("resume-candidates", str(self.repo_root))

        self.assertEqual(result.returncode, 0, result.stderr)
        candidates = json.loads(result.stdout)
        self.assertEqual([c["run_id"] for c in candidates], [data["run_id"]])


if __name__ == "__main__":
    unittest.main()
