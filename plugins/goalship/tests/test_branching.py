"""Tests for goalship's branch operations and dependency-aware branching.

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

    def test_dependency_pr_lookup_failure_does_not_silently_resolve_to_trunk(self):
        # #2: pr_state() returning None means the lookup itself failed (an
        # expired credential, a host outage) — distinct from a
        # legitimately closed PR. Folding it into "closed" would silently
        # rebase a dependent ticket onto trunk instead of its still-open
        # predecessor's branch during a transient outage.
        dep_id = self._tk_create("Dependency with an unresolvable PR")
        lr.record_claim_note(self.repo_root, dep_id, "feat/dep-branch")
        lr.record_ship_note(self.repo_root, dep_id, "feat/dep-branch", "https://example.com/pr/1", "sha1")

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        with mock.patch.object(lr, "pr_state", return_value=None):
            with self.assertRaises(RuntimeError):
                lr.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh")


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


class TestClaimIdempotency(TicketBranchingTestCase):
    """#9: a crash between create_branch and record_claim_note leaves a real
    branch with zero notes. cmd_claim must self-heal on retry instead of
    failing on "branch already exists" or leaving the claim note unwritten."""

    def test_claim_retried_after_a_crash_before_the_note_self_heals(self):
        ticket_id = self._tk_create("Claim retried after a crash")
        # Simulate the crash: branch already created (and left checked
        # out), claim note never written — then a fresh process retries.
        lr.create_branch(self.repo_root, "feat/crash-before-note", "origin/main")
        _run(["git", "checkout", "main"], self.repo_root)

        lr.cmd_claim([str(self.repo_root), ticket_id, "feat/crash-before-note", "origin/main", "main"])

        fields = lr.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("branch"), "feat/crash-before-note")
        current = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(current.stdout.strip(), "feat/crash-before-note")

    def test_fresh_claim_still_creates_the_branch_as_normal(self):
        ticket_id = self._tk_create("Fresh claim")
        lr.cmd_claim([str(self.repo_root), ticket_id, "feat/fresh-claim", "origin/main", "main"])

        fields = lr.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("branch"), "feat/fresh-claim")
        self.assertIn("feat/fresh-claim", self._local_branches())


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
        # .tickets/ is never tracked or git-ignored by this tool — a
        # plain `git clean -fd` on abort would wipe out the entire ticket
        # store the moment any gate ever fails.
        lr.create_branch(self.repo_root, "feat/will-fail-2", "origin/main")
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        (self.repo_root / "half-done.txt").write_text("broken\n")

        lr.reset_to_clean_base(self.repo_root, "main")

        self.assertTrue((self.repo_root / ".tickets" / "T-1.md").exists())
        self.assertFalse((self.repo_root / "half-done.txt").exists())


class TestBranchHasCommits(BranchingTestCase):
    """Crash-recovery check (retry_pr_creation): whether `branch` has
    any commits not on `base`, distinguishing a fresh-implementation crash
    (nothing to retry-push) from a push/PR-creation-only crash (commit
    survived, only the network step failed)."""

    def test_false_when_branch_has_no_commits_past_base(self):
        lr.create_branch(self.repo_root, "feat/empty", "origin/main")
        self.assertFalse(lr.branch_has_commits(self.repo_root, "main", "feat/empty"))

    def test_true_when_branch_has_commits_past_base(self):
        lr.create_branch(self.repo_root, "feat/has-commits", "origin/main")
        (self.repo_root / "file.txt").write_text("x\n")
        lr.commit_all(self.repo_root, "feat: add file")
        self.assertTrue(lr.branch_has_commits(self.repo_root, "main", "feat/has-commits"))


class TestHeadShaForRef(BranchingTestCase):
    """head_sha() defaults to HEAD (its only prior caller, commit_all, needs
    exactly that) but must also resolve an arbitrary ref — the
    retry_pr_creation crash-recovery path needs a branch's tip while HEAD is
    on a different checkout."""

    def test_defaults_to_head(self):
        expected = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(lr.head_sha(self.repo_root), expected)

    def test_resolves_an_arbitrary_ref_without_checking_it_out(self):
        lr.create_branch(self.repo_root, "feat/other-branch", "origin/main")
        (self.repo_root / "file.txt").write_text("x\n")
        branch_sha = lr.commit_all(self.repo_root, "feat: add file")
        _run(["git", "checkout", "main"], self.repo_root)

        self.assertEqual(lr.head_sha(self.repo_root, "feat/other-branch"), branch_sha)
        self.assertNotEqual(lr.head_sha(self.repo_root), branch_sha)


class TestCreatePullRequest(unittest.TestCase):
    """PR creation is a safety-critical mechanical operation, so it
    lives in the script (covered by the AST guardrail below) rather than in
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
    """The retarget_base_merged outcome: a stacked ticket's dependency
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


class TestPrState(unittest.TestCase):
    """#4: pr_state()'s own gh/glab argv construction, JSON parsing, and
    state-string mapping — every other test in this suite mocks pr_state
    itself, so exercise it directly here against a patched subprocess.run."""

    def _fake_run(self, returncode=0, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_gh_open_maps_to_open_with_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._fake_run(stdout="OPEN\n")

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            state = lr.pr_state(Path("/repo"), "gh", "42")

        self.assertEqual(state, "open")
        self.assertEqual(
            captured["argv"],
            ["gh", "pr", "view", "42", "--json", "state", "-q", ".state"],
        )

    def test_gh_merged_maps_to_merged(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="MERGED\n")):
            self.assertEqual(lr.pr_state(Path("/repo"), "gh", "42"), "merged")

    def test_gh_closed_maps_to_closed(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="CLOSED\n")):
            self.assertEqual(lr.pr_state(Path("/repo"), "gh", "42"), "closed")

    def test_gh_nonzero_returncode_returns_none(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(returncode=1, stderr="not found")):
            self.assertIsNone(lr.pr_state(Path("/repo"), "gh", "42"))

    def test_glab_opened_maps_to_open_with_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._fake_run(stdout='{"state": "opened"}')

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            state = lr.pr_state(Path("/repo"), "glab", "7")

        self.assertEqual(state, "open")
        self.assertEqual(captured["argv"], ["glab", "mr", "view", "7", "-F", "json"])

    def test_glab_merged_maps_to_merged(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout='{"state": "merged"}')):
            self.assertEqual(lr.pr_state(Path("/repo"), "glab", "7"), "merged")

    def test_glab_closed_maps_to_closed(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout='{"state": "closed"}')):
            self.assertEqual(lr.pr_state(Path("/repo"), "glab", "7"), "closed")

    def test_glab_invalid_json_returns_none_not_raises(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="not json")):
            self.assertIsNone(lr.pr_state(Path("/repo"), "glab", "7"))

    def test_glab_nonzero_returncode_returns_none(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(returncode=1)):
            self.assertIsNone(lr.pr_state(Path("/repo"), "glab", "7"))

    def test_unsupported_host_tool_returns_none_without_calling_subprocess(self):
        with mock.patch.object(lr.subprocess, "run") as mock_run:
            state = lr.pr_state(Path("/repo"), "hub", "1")
        self.assertIsNone(state)
        mock_run.assert_not_called()

    def test_none_host_tool_returns_none(self):
        self.assertIsNone(lr.pr_state(Path("/repo"), None, "1"))


class TestNoDestructiveOperations(unittest.TestCase):
    """The script exposes no merge, approve, force-push, arbitrary
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

    def _iter_run_calls_with_scope(self, tree):
        """Yield (call_node, enclosing_scope) for every `*.run(...)` call in
        `tree`, where `enclosing_scope` is the nearest enclosing
        FunctionDef (or `tree` itself for module-level calls) — the scope
        `_resolve_call_argv` searches to resolve a `Name` arg back to the
        list it was assigned from."""
        def walk(node, scope):
            if isinstance(node, ast.FunctionDef):
                scope = node
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "run"):
                yield node, scope
            for child in ast.iter_child_nodes(node):
                yield from walk(child, scope)
        yield from walk(tree, tree)

    def _resolve_call_argv(self, call_node, scope):
        """Best-effort argv token extraction for a `*.run(...)` call: an
        inline list literal (`subprocess.run(["gh", ...])`), or a `name =
        [...]` local variable assigned earlier in `scope`
        (`create_pull_request`/`retarget_pull_request` build argv this way
        before calling `subprocess.run(argv, ...)`). Returns None for argv
        this can't statically resolve (e.g. built by list concatenation or
        passed in as a parameter) rather than guessing.
        """
        if not call_node.args:
            return None
        arg0 = call_node.args[0]
        if isinstance(arg0, ast.List):
            list_nodes = [arg0]
        elif isinstance(arg0, ast.Name):
            list_nodes = [
                stmt.value
                for stmt in ast.walk(scope)
                if isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.List)
                and any(isinstance(t, ast.Name) and t.id == arg0.id for t in stmt.targets)
            ]
        else:
            list_nodes = []
        if not list_nodes:
            return None
        tokens = []
        for list_node in list_nodes:
            tokens.extend(
                elt.value for elt in list_node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            )
        return tokens

    def test_no_subprocess_call_carries_a_forbidden_argv_token(self):
        for call_node, scope in self._iter_run_calls_with_scope(self.tree):
            argv = self._resolve_call_argv(call_node, scope)
            if argv is None:
                continue
            hit = self.FORBIDDEN_ARGV_TOKENS.intersection(argv)
            self.assertFalse(
                hit, f"subprocess call {argv!r} carries forbidden token(s) {hit!r}",
            )

    def test_local_variable_argv_with_forbidden_token_is_detected(self):
        """The guardrail above also covers argv built into a local variable before being passed
        to subprocess.run(argv, ...) — the pattern create_pull_request and
        retarget_pull_request use — not just an inline list literal passed
        directly as the call's first argument."""
        snippet = (
            "def create_pull_request(repo_root, host_tool, branch, base):\n"
            "    if host_tool == 'gh':\n"
            "        argv = ['gh', 'pr', 'merge', branch]\n"
            "    subprocess.run(argv, check=True)\n"
        )
        tree = ast.parse(snippet)
        call_node, scope = next(iter(self._iter_run_calls_with_scope(tree)))

        argv = self._resolve_call_argv(call_node, scope)

        self.assertIsNotNone(argv, "walker failed to resolve argv from a local variable assignment")
        assert argv is not None
        self.assertTrue(
            self.FORBIDDEN_ARGV_TOKENS.intersection(argv),
            f"walker resolved {argv!r} but missed its forbidden token",
        )


if __name__ == "__main__":
    unittest.main()
