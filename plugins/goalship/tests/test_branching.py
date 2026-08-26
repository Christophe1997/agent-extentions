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
import branching  # noqa: E402
import preflight  # noqa: E402
import reconciliation  # noqa: E402
import run_state  # noqa: E402


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
        self.assertEqual(branching.resolve_branch_base("main", []), "main")

    def test_single_open_dependency_uses_its_branch(self):
        deps = [branching.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="open")]
        self.assertEqual(branching.resolve_branch_base("main", deps), "feat/dep-a")

    def test_merged_dependency_uses_trunk_not_stale_branch(self):
        deps = [branching.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="merged")]
        self.assertEqual(branching.resolve_branch_base("main", deps), "main")

    def test_closed_unmerged_dependency_uses_trunk(self):
        deps = [branching.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="closed")]
        self.assertEqual(branching.resolve_branch_base("main", deps), "main")

    def test_fan_in_two_simultaneously_open_dependencies_uses_trunk(self):
        deps = [
            branching.DependencyPR(ticket_id="T-1", branch="feat/dep-a", state="open"),
            branching.DependencyPR(ticket_id="T-2", branch="feat/dep-b", state="open"),
        ]
        self.assertEqual(branching.resolve_branch_base("main", deps), "main")


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
        self.assertEqual(branching.resolve_base_for_ticket(self.repo_root, ticket_id, "main"), "main")

    def test_single_open_dependency_resolves_to_its_branch(self):
        dep_id = self._tk_create("Dependency")
        reconciliation.record_claim_note(self.repo_root, dep_id, "feat/dep-branch")
        reconciliation.record_ship_note(self.repo_root, dep_id, "feat/dep-branch", "https://example.com/pr/1", "sha1")

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        with mock.patch.object(reconciliation, "pr_state", return_value="open"):
            base = branching.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh")
        self.assertEqual(base, "feat/dep-branch")

    def test_merged_dependency_resolves_to_trunk(self):
        dep_id = self._tk_create("Dependency")
        reconciliation.record_claim_note(self.repo_root, dep_id, "feat/dep-branch")
        reconciliation.record_ship_note(self.repo_root, dep_id, "feat/dep-branch", "https://example.com/pr/1", "sha1")

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        with mock.patch.object(reconciliation, "pr_state", return_value="merged"):
            base = branching.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh")
        self.assertEqual(base, "main")

    def test_dependency_never_claimed_by_this_tool_resolves_to_trunk(self):
        # A predecessor with no recorded branch note (closed by hand, or
        # predates this loop) can't be looked up — treated as resolved.
        dep_id = self._tk_create("Manually closed dependency")
        subprocess.run(["tk", "close", dep_id], cwd=self.repo_root, check=True, capture_output=True)

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        self.assertEqual(branching.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh"), "main")

    def test_dependency_pr_lookup_failure_does_not_silently_resolve_to_trunk(self):
        # pr_state() returning None means the lookup itself failed (an
        # expired credential, a host outage) — distinct from a
        # legitimately closed PR. Folding it into "closed" would silently
        # rebase a dependent ticket onto trunk instead of its still-open
        # predecessor's branch during a transient outage.
        dep_id = self._tk_create("Dependency with an unresolvable PR")
        reconciliation.record_claim_note(self.repo_root, dep_id, "feat/dep-branch")
        reconciliation.record_ship_note(self.repo_root, dep_id, "feat/dep-branch", "https://example.com/pr/1", "sha1")

        ticket_id = self._tk_create("Dependent")
        subprocess.run(["tk", "dep", ticket_id, dep_id], cwd=self.repo_root, check=True, capture_output=True)

        with mock.patch.object(reconciliation, "pr_state", return_value=None):
            with self.assertRaises(RuntimeError):
                branching.resolve_base_for_ticket(self.repo_root, ticket_id, "main", "gh")


class TestBranchNaming(BranchingTestCase):
    def test_slugifies_type_and_title(self):
        name = branching.branch_name_for_ticket(self.repo_root, "feat", "Add input validation!")
        self.assertEqual(name, "feat/add-input-validation")

    def test_collision_applies_numeric_suffix(self):
        first = branching.branch_name_for_ticket(self.repo_root, "feat", "Add login form")
        branching.create_branch(self.repo_root, first, "origin/main")

        second = branching.branch_name_for_ticket(self.repo_root, "feat", "Add login form")
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

        name = branching.branch_name_for_ticket(self.repo_root, "feat", "existing remote only")
        self.assertEqual(name, "feat/existing-remote-only-2")


class TestClaimIdempotency(TicketBranchingTestCase):
    """A crash between create_branch and record_claim_note leaves a real
    branch with zero notes. cmd_claim must self-heal on retry instead of
    failing on "branch already exists" or leaving the claim note unwritten."""

    def test_claim_retried_after_a_crash_before_the_note_self_heals(self):
        ticket_id = self._tk_create("Claim retried after a crash")
        # Simulate the crash: branch already created (and left checked
        # out), claim note never written — then a fresh process retries.
        branching.create_branch(self.repo_root, "feat/crash-before-note", "origin/main")
        _run(["git", "checkout", "main"], self.repo_root)

        lr.cmd_claim([str(self.repo_root), ticket_id, "feat/crash-before-note", "origin/main", "main"])

        fields = reconciliation.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("branch"), "feat/crash-before-note")
        current = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(current.stdout.strip(), "feat/crash-before-note")

    def test_fresh_claim_still_creates_the_branch_as_normal(self):
        ticket_id = self._tk_create("Fresh claim")
        lr.cmd_claim([str(self.repo_root), ticket_id, "feat/fresh-claim", "origin/main", "main"])

        fields = reconciliation.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("branch"), "feat/fresh-claim")
        self.assertIn("feat/fresh-claim", self._local_branches())


class TestRecordClaimNoteClaimSha(TicketBranchingTestCase):
    """claim_sha is the branch's tip at claim time — the baseline
    commit_landed_since compares against to tell whether this ticket's own
    work has landed, not merely whether the branch has any commits past
    its base at all."""

    def test_writes_claim_sha_field_when_given(self):
        ticket_id = self._tk_create("Claim note with claim_sha")
        reconciliation.record_claim_note(self.repo_root, ticket_id, "feat/x", claim_sha="abc123")
        fields = reconciliation.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("branch"), "feat/x")
        self.assertEqual(fields.get("claim_sha"), "abc123")

    def test_omits_claim_sha_field_when_not_given(self):
        ticket_id = self._tk_create("Claim note without claim_sha")
        reconciliation.record_claim_note(self.repo_root, ticket_id, "feat/x")
        self.assertNotIn("claim_sha", reconciliation.note_fields_for_ticket(self.repo_root, ticket_id))


class TestClaimRecordsClaimSha(TicketBranchingTestCase):
    """cmd_claim must capture the branch's tip as claim_sha on both paths:
    a fresh branch (tip == base_ref) and the crash-recovery retry
    (checking out an already-created branch) — nothing has been implemented
    on either branch yet, so both should equal origin/main's own tip."""

    def test_fresh_claim_records_the_branchs_tip_as_claim_sha(self):
        ticket_id = self._tk_create("Fresh claim records claim_sha")
        lr.cmd_claim([str(self.repo_root), ticket_id, "feat/fresh", "origin/main", "main"])
        fields = reconciliation.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("claim_sha"), branching.head_sha(self.repo_root, "origin/main"))

    def test_crash_before_note_retry_records_the_branchs_tip_as_claim_sha(self):
        ticket_id = self._tk_create("Crash-recovery claim records claim_sha")
        # Crash-recovery setup: branch already created and left checked out, note never written.
        branching.create_branch(self.repo_root, "feat/crash-recovery", "origin/main")
        _run(["git", "checkout", "main"], self.repo_root)

        lr.cmd_claim([str(self.repo_root), ticket_id, "feat/crash-recovery", "origin/main", "main"])

        fields = reconciliation.note_fields_for_ticket(self.repo_root, ticket_id)
        self.assertEqual(fields.get("claim_sha"), branching.head_sha(self.repo_root, "origin/main"))


class TestFindRunBranch(TicketBranchingTestCase):
    """Shared-branch mode: discover a run's already-claimed branch from its
    own claimed tickets' notes, rather than a new ledger field — lets
    ticket 2..N of a run reuse ticket 1's branch."""

    def test_empty_claimed_list_returns_none(self):
        self.assertIsNone(reconciliation.find_run_branch(self.repo_root, []))

    def test_claimed_ticket_with_no_branch_note_returns_none(self):
        ticket_id = self._tk_create("Claimed but not yet branched")
        self.assertIsNone(reconciliation.find_run_branch(self.repo_root, [ticket_id]))

    def test_returns_the_claimed_tickets_branch(self):
        ticket_id = self._tk_create("Claimed and branched")
        reconciliation.record_claim_note(self.repo_root, ticket_id, "feat/shared-goal")
        self.assertEqual(reconciliation.find_run_branch(self.repo_root, [ticket_id]), "feat/shared-goal")

    def test_finds_it_regardless_of_which_claimed_ticket_carries_it(self):
        first = self._tk_create("First ticket, no branch note yet")
        second = self._tk_create("Second ticket, already branched")
        reconciliation.record_claim_note(self.repo_root, second, "feat/shared-goal")
        self.assertEqual(reconciliation.find_run_branch(self.repo_root, [first, second]), "feat/shared-goal")


class TestBranchLifecycle(BranchingTestCase):
    def test_create_branch_off_trunk(self):
        branching.create_branch(self.repo_root, "feat/off-trunk", "origin/main")
        result = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "feat/off-trunk")

    def test_commit_and_push(self):
        branching.create_branch(self.repo_root, "feat/ship-me", "origin/main")
        (self.repo_root / "new-file.txt").write_text("content\n")
        sha = branching.commit_all(self.repo_root, "feat: add new-file")
        self.assertTrue(sha)
        branching.push_branch(self.repo_root, "feat/ship-me")

        remote_log = subprocess.run(
            ["git", "log", "-1", "--format=%H", "origin/feat/ship-me"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(remote_log.stdout.strip(), sha)

    def test_dirty_paths_ignores_tickets_dir(self):
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        self.assertEqual(preflight.dirty_paths(self.repo_root), [])

    def test_commit_all_never_sweeps_in_the_tickets_dir(self):
        # tk mutates .tickets/ as a routine side effect of `tk start` /
        # `tk add-note` during this very loop — those writes must never
        # ride along on a ticket's own implementation commit.
        branching.create_branch(self.repo_root, "feat/no-tickets-sweep", "origin/main")
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        (self.repo_root / "feature.txt").write_text("impl\n")

        branching.commit_all(self.repo_root, "feat: add feature")

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
        run_state.ensure_ledger_excluded(self.repo_root)
        branching.create_branch(self.repo_root, "feat/already-excluded", "origin/main")
        (self.repo_root / ".goalship").mkdir()
        (self.repo_root / ".goalship" / "state.json").write_text("{}\n")
        (self.repo_root / "feature.txt").write_text("impl\n")

        branching.commit_all(self.repo_root, "feat: add feature")

        committed = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=self.repo_root, capture_output=True, text=True, check=True,
        ).stdout.split()
        self.assertEqual(committed, ["feature.txt"])

    def test_gate_failure_resets_working_tree_to_clean_trunk(self):
        branching.create_branch(self.repo_root, "feat/will-fail", "origin/main")
        (self.repo_root / "half-done.txt").write_text("broken\n")
        self.assertNotEqual(preflight.dirty_paths(self.repo_root), [])

        branching.reset_to_clean_base(self.repo_root, "main")

        current = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo_root,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(current.stdout.strip(), "main")
        self.assertEqual(preflight.dirty_paths(self.repo_root), [])
        self.assertFalse((self.repo_root / "half-done.txt").exists())

    def test_gate_failure_reset_never_deletes_the_untracked_tickets_dir(self):
        # .tickets/ is never tracked or git-ignored by this tool — a
        # plain `git clean -fd` on abort would wipe out the entire ticket
        # store the moment any gate ever fails.
        branching.create_branch(self.repo_root, "feat/will-fail-2", "origin/main")
        (self.repo_root / ".tickets").mkdir()
        (self.repo_root / ".tickets" / "T-1.md").write_text("# T-1\n")
        (self.repo_root / "half-done.txt").write_text("broken\n")

        branching.reset_to_clean_base(self.repo_root, "main")

        self.assertTrue((self.repo_root / ".tickets" / "T-1.md").exists())
        self.assertFalse((self.repo_root / "half-done.txt").exists())


class TestCommitLandedSince(BranchingTestCase):
    """Ticket-scoped crash-recovery check (retry_pr_creation): whether a
    commit has landed on `branch` since a specific ticket's own claim_sha —
    unlike a branch-wide "any commits past base at all" check, this isn't
    fooled by commits that were already on the branch before this ticket
    claimed it (the shape a shared branch takes once more than one ticket
    lands on it)."""

    def test_false_immediately_after_claim_with_no_new_commit(self):
        branching.create_branch(self.repo_root, "feat/x", "origin/main")
        claim_sha = branching.head_sha(self.repo_root)
        self.assertFalse(branching.commit_landed_since(self.repo_root, "feat/x", claim_sha))

    def test_true_once_a_commit_lands_after_claim(self):
        branching.create_branch(self.repo_root, "feat/x", "origin/main")
        claim_sha = branching.head_sha(self.repo_root)
        (self.repo_root / "file.txt").write_text("x\n")
        branching.commit_all(self.repo_root, "feat: add file")
        self.assertTrue(branching.commit_landed_since(self.repo_root, "feat/x", claim_sha))

    def test_not_fooled_by_commits_that_predate_this_tickets_own_claim(self):
        # Simulates a shared branch: commits already there before this
        # ticket's own claim_sha was captured (a predecessor ticket's
        # already-landed work). A branch-wide "any commits past base at
        # all" check would report True here and misattribute that work to
        # this ticket; commit_landed_since must not be fooled the same way.
        branching.create_branch(self.repo_root, "feat/shared", "origin/main")
        (self.repo_root / "predecessor.txt").write_text("done\n")
        branching.commit_all(self.repo_root, "feat: predecessor's work")

        claim_sha = branching.head_sha(self.repo_root)  # this ticket's own claim, after the above

        self.assertFalse(branching.commit_landed_since(self.repo_root, "feat/shared", claim_sha))

        (self.repo_root / "own-work.txt").write_text("this ticket's work\n")
        branching.commit_all(self.repo_root, "feat: this ticket's own work")
        self.assertTrue(branching.commit_landed_since(self.repo_root, "feat/shared", claim_sha))


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
        self.assertEqual(branching.head_sha(self.repo_root), expected)

    def test_resolves_an_arbitrary_ref_without_checking_it_out(self):
        branching.create_branch(self.repo_root, "feat/other-branch", "origin/main")
        (self.repo_root / "file.txt").write_text("x\n")
        branch_sha = branching.commit_all(self.repo_root, "feat: add file")
        _run(["git", "checkout", "main"], self.repo_root)

        self.assertEqual(branching.head_sha(self.repo_root, "feat/other-branch"), branch_sha)
        self.assertNotEqual(branching.head_sha(self.repo_root), branch_sha)


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
            url = branching.create_pull_request(
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
            url = branching.create_pull_request(
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
            branching.create_pull_request(Path("/repo"), "hub", "feat/x", "main", "t", "b")

    def test_missing_url_in_output_raises(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run("no url here\n")):
            with self.assertRaises(RuntimeError):
                branching.create_pull_request(Path("/repo"), "gh", "feat/x", "main", "t", "b")


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
            branching.retarget_pull_request(Path("/repo"), "gh", "42", "main")

        self.assertEqual(captured["argv"], ["gh", "pr", "edit", "42", "--base", "main"])

    def test_glab_builds_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            branching.retarget_pull_request(Path("/repo"), "glab", "7", "main")

        self.assertEqual(captured["argv"], ["glab", "mr", "update", "7", "--target-branch", "main"])

    def test_unsupported_host_tool_raises(self):
        with self.assertRaises(ValueError):
            branching.retarget_pull_request(Path("/repo"), "hub", "1", "main")


class TestPrState(unittest.TestCase):
    """Covers pr_state()'s own gh/glab argv construction, JSON parsing, and
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
            state = reconciliation.pr_state(Path("/repo"), "gh", "42")

        self.assertEqual(state, "open")
        self.assertEqual(
            captured["argv"],
            ["gh", "pr", "view", "42", "--json", "state", "-q", ".state"],
        )

    def test_gh_merged_maps_to_merged(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="MERGED\n")):
            self.assertEqual(reconciliation.pr_state(Path("/repo"), "gh", "42"), "merged")

    def test_gh_closed_maps_to_closed(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="CLOSED\n")):
            self.assertEqual(reconciliation.pr_state(Path("/repo"), "gh", "42"), "closed")

    def test_gh_nonzero_returncode_returns_none(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(returncode=1, stderr="not found")):
            self.assertIsNone(reconciliation.pr_state(Path("/repo"), "gh", "42"))

    def test_glab_opened_maps_to_open_with_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._fake_run(stdout='{"state": "opened"}')

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            state = reconciliation.pr_state(Path("/repo"), "glab", "7")

        self.assertEqual(state, "open")
        self.assertEqual(captured["argv"], ["glab", "mr", "view", "7", "-F", "json"])

    def test_glab_merged_maps_to_merged(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout='{"state": "merged"}')):
            self.assertEqual(reconciliation.pr_state(Path("/repo"), "glab", "7"), "merged")

    def test_glab_closed_maps_to_closed(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout='{"state": "closed"}')):
            self.assertEqual(reconciliation.pr_state(Path("/repo"), "glab", "7"), "closed")

    def test_glab_invalid_json_returns_none_not_raises(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="not json")):
            self.assertIsNone(reconciliation.pr_state(Path("/repo"), "glab", "7"))

    def test_glab_nonzero_returncode_returns_none(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(returncode=1)):
            self.assertIsNone(reconciliation.pr_state(Path("/repo"), "glab", "7"))

    def test_unsupported_host_tool_returns_none_without_calling_subprocess(self):
        with mock.patch.object(lr.subprocess, "run") as mock_run:
            state = reconciliation.pr_state(Path("/repo"), "hub", "1")
        self.assertIsNone(state)
        mock_run.assert_not_called()

    def test_none_host_tool_returns_none(self):
        self.assertIsNone(reconciliation.pr_state(Path("/repo"), None, "1"))


class TestFindOpenPrForBranch(unittest.TestCase):
    """Commit-mode PR reuse: is there already an open PR/MR for this
    branch? Queried directly against the host (not the run-state ledger),
    same ledger-independence reasoning as reconcile() itself — a lost
    ledger must not strand a run's shared-PR discovery."""

    def _fake_run(self, returncode=0, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_gh_returns_the_first_open_prs_url_with_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._fake_run(stdout='[{"url": "https://github.com/o/r/pull/9"}]')

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            url = reconciliation.find_open_pr_for_branch(Path("/repo"), "gh", "feat/shared-goal")

        self.assertEqual(url, "https://github.com/o/r/pull/9")
        self.assertEqual(
            captured["argv"],
            ["gh", "pr", "list", "--head", "feat/shared-goal", "--state", "open", "--json", "url"],
        )

    def test_gh_returns_none_when_no_open_pr(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="[]")):
            self.assertIsNone(reconciliation.find_open_pr_for_branch(Path("/repo"), "gh", "feat/x"))

    def test_gh_nonzero_returncode_returns_none(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(returncode=1)):
            self.assertIsNone(reconciliation.find_open_pr_for_branch(Path("/repo"), "gh", "feat/x"))

    def test_glab_returns_the_first_open_mrs_web_url_with_expected_argv(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._fake_run(stdout='[{"web_url": "https://gitlab.com/o/r/-/merge_requests/9"}]')

        with mock.patch.object(lr.subprocess, "run", side_effect=fake_run):
            url = reconciliation.find_open_pr_for_branch(Path("/repo"), "glab", "feat/shared-goal")

        self.assertEqual(url, "https://gitlab.com/o/r/-/merge_requests/9")
        self.assertEqual(
            captured["argv"],
            ["glab", "mr", "list", "--source-branch", "feat/shared-goal", "-F", "json"],
        )

    def test_glab_returns_none_when_no_open_mr(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="[]")):
            self.assertIsNone(reconciliation.find_open_pr_for_branch(Path("/repo"), "glab", "feat/x"))

    def test_invalid_json_returns_none_not_raises(self):
        with mock.patch.object(lr.subprocess, "run", return_value=self._fake_run(stdout="not json")):
            self.assertIsNone(reconciliation.find_open_pr_for_branch(Path("/repo"), "gh", "feat/x"))

    def test_unsupported_host_tool_returns_none_without_calling_subprocess(self):
        with mock.patch.object(lr.subprocess, "run") as mock_run:
            url = reconciliation.find_open_pr_for_branch(Path("/repo"), "hub", "feat/x")
        self.assertIsNone(url)
        mock_run.assert_not_called()


class TestNoDestructiveOperations(unittest.TestCase):
    """scripts/*.py exposes no merge, approve, force-push, arbitrary
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
        # loop_runner.py dispatches to sibling modules (run_state.py,
        # preflight.py, reconciliation.py, branching.py) rather than doing
        # git/gh/glab work itself — glob the whole directory so this
        # guardrail still covers wherever a subprocess.run call actually
        # lives, not just the CLI dispatcher.
        self.modules = [
            (path, ast.parse(path.read_text(), filename=str(path)))
            for path in sorted(_SCRIPTS.glob("*.py"))
        ]

    def _public_function_names(self):
        return [
            (path, node.name)
            for path, tree in self.modules
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ]

    def test_no_public_function_names_a_forbidden_operation(self):
        for path, name in self._public_function_names():
            lowered = name.lower()
            for forbidden in self.FORBIDDEN_FUNCTION_SUBSTRINGS:
                self.assertNotIn(
                    forbidden, lowered,
                    f"{path.name}: public function {name!r} suggests a forbidden operation ({forbidden!r})",
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
        for path, tree in self.modules:
            for call_node, scope in self._iter_run_calls_with_scope(tree):
                argv = self._resolve_call_argv(call_node, scope)
                if argv is None:
                    continue
                hit = self.FORBIDDEN_ARGV_TOKENS.intersection(argv)
                self.assertFalse(
                    hit, f"{path.name}: subprocess call {argv!r} carries forbidden token(s) {hit!r}",
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
