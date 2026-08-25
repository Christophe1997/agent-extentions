"""Tests for goalship's branch operations and dependency-aware branching
(R4, R5, R8; KTD3, KTD4, and the Product Contract's dependency-aware
branch model Key Decision).

Run from the repo root:
    python3 -m pytest plugins/goalship/tests/test_branching.py -v
"""
from __future__ import annotations

import ast
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


class BranchingTestCase(unittest.TestCase):
    """A repo_root clone of a bare `origin`, with an initial commit on main."""

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
        _run(["git", "fetch", "-q", "origin"], self.repo_root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _local_branches(self):
        result = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}


class TestResolveBranchBase(unittest.TestCase):
    """Pure decision logic — the dependency-aware branch model Key Decision."""

    def test_no_dependencies_uses_trunk(self):
        self.assertEqual(lr.resolve_branch_base("main", []), "main")

    def test_single_open_dependency_uses_its_branch(self):
        deps = [lr.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="open")]
        self.assertEqual(lr.resolve_branch_base("main", deps), "feat/dep-a")

    def test_merged_dependency_uses_trunk_not_stale_branch(self):
        deps = [lr.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="merged")]
        self.assertEqual(lr.resolve_branch_base("main", deps), "main")

    def test_closed_unmerged_dependency_uses_trunk(self):
        deps = [lr.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="closed")]
        self.assertEqual(lr.resolve_branch_base("main", deps), "main")

    def test_fan_in_two_simultaneously_open_dependencies_uses_trunk(self):
        deps = [
            lr.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="open"),
            lr.DependencyPR(ticket_id="T-2", branch="feat/dep-b", state="open"),
        ]
        self.assertEqual(lr.resolve_branch_base("main", deps), "main")


class TicketBranchingTestCase(BranchingTestCase):
    """A repo_root that is both a git repo (with a bare origin) and a `tk`
    ticket store — resolve_base_for_ticket needs both."""

    def _tk_create(self, title: str) -> str:
        result = subprocess.run(
            ["tk", "create", title, "-t", "task"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip().splitlines()[-1]


class TestResolveBaseForTicket(TicketBranchingTestCase):
    def test_no_dependencies_resolves_to_trunk(self):
        ticket_id = self._tk_create("Standalone ticket")
        self.assertEqual(lr.resolve_base_for_ticket(self.repo_root, ticket_id, "main"), "main")

    def test_single_open_dependency_resolves_to_its_branch(self):
        dep_id = self._tk_create("Dependency")
        lr.record_claim_note(self.repo_root, dep_id, "feat/dep-branch")
        lr.record_ship_note(self.repo_root, dep_id, "feat/dep-branch", "https://example.com/pr/1", "sha1")

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        with mock.patch.object(lr, "pr_state", return_value="open"):
            base = lr.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh")
        self.assertEqual(base, "feat/dep-branch")

    def test_merged_dependency_resolves_to_trunk(self):
        dep_id = self._tk_create("Dependency")
        lr.record_claim_note(self.repo_root, dep_id, "feat/dep-branch")
        lr.record_ship_note(self.repo_root, dep_id, "feat/dep-branch", "https://example.com/pr/1", "sha1")

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        with mock.patch.object(lr, "pr_state", return_value="merged"):
            base = lr.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh")
        self.assertEqual(base, "main")

    def test_dependency_never_claimed_by_this_tool_resolves_to_trunk(self):
        # A predecessor with no recorded branch note (closed by hand, or
        # predates this loop) can't be looked up — treated as resolved.
        dep_id = self._tk_create("Manually closed dependency")
        subprocess.run(["tk", "close", dep_id], cwd=self.repo_root, check=True, capture_output=True)

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        self.assertEqual(lr.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh"), "main")


class TestBranchNaming(BranchingTestCase):
    def test_slugifies_type_and_title(self):
        name = lr.branch_name_for_ticket(self.repo_root, "feat", "Add input validation!")
        self.assertEqual(name, "feat/add-input-validation")

    def test_collision_applies_numeric_suffix(self):
        first = lr.branch_name_for_ticket(self.repo_root, "feat", "Add login form")
        lr.create_branch(self.repo_root, first, "origin/main")

        second = lr.branch_name_for_ticket(self.repo_root, "feat", "Add login form")
        self.assertNotEqual(first, second)
        self.assertEqual(second, f"{first}-2")

    def test_collision_checked_against_remote_refs_too(self):
        # A branch that exists only on origin (e.g. from a prior run) must
        # still be treated as taken.
        _run(["git", "checkout", "-b", "feat/existing-remote-only"], self.repo_root)
        _run(["git", "push", "-q", "-u", "origin", "feat/existing-remote-only"], self.repo_root)
        _run(["git", "checkout", "main"], self.repo_root)
        _run(["git", "branch", "-D", "feat/existing-remote-only"], self.repo_root)
        _run(["git", "fetch", "-q", "origin"], self.repo_root)

        name = lr.branch_name_for_ticket(self.repo_root, "feat", "existing remote only")
        self.assertEqual(name, "feat/existing-remote-only-2")


class TestBranchLifecycle(BranchingTestCase):
    def test_create_branch_off_trunk(self):
        lr.create_branch(self.repo_root, "feat/off-trunk", "origin/main")
        result = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "feat/off-trunk")

    def test_commit_and_push(self):
        lr.create_branch(self.repo_root, "feat/ship-me", "origin/main")
        (self.repo_root / "new-file.txt").write_text("content\n")
        sha = lr.commit_all(self.repo_root, "feat: add new-file")
        self.assertTrue(sha)
        lr.push_branch(self.repo_root, "feat/ship-me")

        remote_log = subprocess.run(
            ["git", "log", "-1", "--format=%H", "origin/feat/ship-me"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(remote_log.stdout.strip(), sha)

    def test_dirty_paths_ignores_tickets_dir(self):
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        self.assertEqual(lr.dirty_paths(self.repo_root), [])

    def test_commit_all_never_sweeps_in_the_tickets_dir(self):
        # tk mutates .tickets/ as a routine side effect of `tk start` /
        # `tk add-note` during this very loop — those writes must never
        # ride along on a ticket's own implementation commit.
        lr.create_branch(self.repo_root, "feat/no-tickets-sweep", "origin/main")
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        (self.repo_root / "feature.txt").write_text("impl\n")

        lr.commit_all(self.repo_root, "feat: add feature")

        committed = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        ).stdout.split()
        self.assertEqual(committed, ["feature.txt"])
        self.assertTrue((self.repo_root / ".tickets" / "T-1.md").exists())

    def test_commit_all_succeeds_once_the_ledger_dir_is_already_git_excluded(self):
        # Every real invocation calls ensure_ledger_excluded (via the
        # `ledger` CLI subcommand) long before the first commit. Once
        # .goalship/ is listed in .git/info/exclude, git's own "ignored
        # file" advice fires — and exits nonzero — for any *explicit*
        # negative pathspec naming an already-ignored path, even though
        # the staging itself is correct either way.
        lr.ensure_ledger_excluded(self.repo_root)
        lr.create_branch(self.repo_root, "feat/already-excluded", "origin/main")
        (self.repo_root / ".goalship").mkdir()
        (self.repo_root / ".goalship" / "state.json").write_text("{}\n")
        (self.repo_root / "feature.txt").write_text("impl\n")

        lr.commit_all(self.repo_root, "feat: add feature")

        committed = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        ).stdout.split()
        self.assertEqual(committed, ["feature.txt"])

    def test_gate_failure_resets_working_tree_to_clean_trunk(self):
        lr.create_branch(self.repo_root, "feat/will-fail", "origin/main")
        (self.repo_root / "half-done.txt").write_text("broken\n")
        self.assertNotEqual(lr.dirty_paths(self.repo_root), [])

        lr.reset_to_clean_base(self.repo_root, "main")

        current = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(current.stdout.strip(), "main")
        self.assertEqual(lr.dirty_paths(self.repo_root), [])
        self.assertFalse((self.repo_root / "half-done.txt").exists())

    def test_gate_failure_reset_never_deletes_the_untracked_tickets_dir(self):
        # .tickets/ is never tracked or git-ignored by this tool (R10) — a
        # plain `git clean -fd` on abort would wipe out the entire ticket
        # store the moment any gate ever fails.
        lr.create_branch(self.repo_root, "feat/will-fail-2", "origin/main")
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        (self.repo_root / "half-done.txt").write_text("broken\n")

        lr.reset_to_clean_base(self.repo_root, "main")

        self.assertTrue((self.repo_root / ".tickets" / "T-1.md").exists())
        self.assertFalse((self.repo_root / "half-done.txt").exists())


class TestCreatePullRequest(unittest.TestCase):
    """KTD1: PR creation is a safety-critical mechanical operation, so it
    lives in the script (covered by the R8 AST guardrail) rather than in
    skill prose that shells out directly."""

    def _fake_run(self, stdout):
        return mock.Mock(returncode=0, stdout=stdout, stderr="")

    def test_gh_builds_expected_argv_and_returns_the_printed_url(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return self._fake_run("https://github.com/acme/widgets/pull/42\n")

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            url = lr.create_pull_request(
                Path("/repo"), "gh", "feat/thing", "main", "feat: thing", "body text",
            )

        self.assertEqual(url, "https://github.com/acme/widgets/pull/42")
        self.assertEqual(
            captured["argv"],
            [
                "gh", "pr", "create",
                "--head", "feat/thing", "--base", "main",
                "--title", "feat: thing", "--body", "body text",
            ],
        )
        self.assertEqual(captured["kwargs"]["cwd"], Path("/repo"))
        self.assertTrue(captured["kwargs"]["check"])

    def test_glab_builds_expected_argv_and_returns_the_printed_url(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._fake_run("https://gitlab.com/acme/widgets/-/merge_requests/7\n")

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            url = lr.create_pull_request(
                Path("/repo"), "glab", "feat/thing", "main", "feat: thing", "body text",
            )

        self.assertEqual(url, "https://gitlab.com/acme/widgets/-/merge_requests/7")
        self.assertEqual(
            captured["argv"],
            [
                "glab", "mr", "create",
                "--source-branch", "feat/thing", "--target-branch", "main",
                "--title", "feat: thing", "--description", "body text", "--yes",
            ],
        )

    def test_unsupported_host_tool_raises(self):
        with self.assertRaises(ValueError):
            lr.create_pull_request(Path("/repo"), "hub", "feat/x", "main", "t", "b")

    def test_missing_url_in_output_raises(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run("no url here\n")):
            with self.assertRaises(RuntimeError):
                lr.create_pull_request(Path("/repo"), "gh", "feat/x", "main", "t", "b")


class TestRetargetPullRequest(unittest.TestCase):
    """KTD8's retarget_base_merged outcome: a stacked ticket's dependency
    merged out from under its already-open PR, so the PR must repoint at
    trunk instead of the now-gone dependency branch."""

    def test_gh_builds_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            lr.retarget_pull_request(Path("/repo"), "gh", "42", "main")

        self.assertEqual(captured["argv"], ["gh", "pr", "edit", "42", "--base", "main"])

    def test_glab_builds_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            lr.retarget_pull_request(Path("/repo"), "glab", "7", "main")

        self.assertEqual(captured["argv"], ["glab", "mr", "update", "7", "--target-branch", "main"])

    def test_unsupported_host_tool_raises(self):
        with self.assertRaises(ValueError):
            lr.retarget_pull_request(Path("/repo"), "hub", "1", "main")


class TestNoDestructiveOperations(unittest.TestCase):
    """R8: the script exposes no merge, approve, force-push, arbitrary
    branch-delete, or publish code path. Asserted against the actual
    source, not just documented behavior."""

    FORBIDDEN_FUNCTION_SUBSTRINGS = (
        "merge", "approve", "force", "delete", "publish", "release",
    )
    # git/gh/glab argv tokens that would perform a forbidden operation.
    FORBIDDEN_ARGV_TOKENS = {
        "merge", "--force", "-f", "-D", "--delete", "publish", "approve",
    }
    # `-f` legitimately appears as a non-git-verb flag in a few commands
    # (none currently); keep an explicit allowlist of (command, flag)
    # pairs that are known-safe if this ever needs one.

    def setUp(self):
        source_path = _SCRIPTS / "loop_runner.py"
        self.source = source_path.read_text()
        self.tree = ast.parse(self.source, filename=str(source_path))

    def _public_function_names(self):
        return [
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ]

    def test_no_public_function_names_a_forbidden_operation(self):
        for name in self._public_function_names():
            lowered = name.lower()
            for forbidden in self.FORBIDDEN_FUNCTION_SUBSTRINGS:
                self.assertNotIn(
                    forbidden, lowered,
                    f"public function {name!r} suggests a forbidden operation ({forbidden!r})",
                )

    def test_no_subprocess_call_carries_a_forbidden_argv_token(self):
        for node in ast.walk(self.tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "run"):
                continue
            if not node.args or not isinstance(node.args[0], ast.List):
                continue
            argv = [
                elt.value for elt in node.args[0].elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            hit = self.FORBIDDEN_ARGV_TOKENS.intersection(argv)
            self.assertFalse(
                hit, f"subprocess call {argv!r} carries forbidden token(s) {hit!r}",
            )


if __name__ == "__main__":
    unittest.main()
