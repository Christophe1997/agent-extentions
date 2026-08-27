"""Tests for goalship's preflight precondition checks.

Run from the repo root:
    python3 -m pytest plugins/goalship/tests/test_preflight.py -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import preflight  # noqa: E402


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def _init_repo_with_remote(path: Path, *, with_remote: bool = True) -> None:
    _run(["git", "init", "-q"], path)
    _run(["git", "config", "user.email", "test@example.com"], path)
    _run(["git", "config", "user.name", "Test"], path)
    (path / "README.md").write_text("placeholder\n")
    _run(["git", "add", "README.md"], path)
    _run(["git", "commit", "-q", "-m", "init"], path)
    _run(["git", "branch", "-m", "main"], path)
    if with_remote:
        bare_dir = tempfile.mkdtemp(suffix="-bare")
        _run(["git", "init", "-q", "--bare", bare_dir], path)
        _run(["git", "remote", "add", "origin", bare_dir], path)
        _run(["git", "push", "-q", "-u", "origin", "main"], path)


class PreflightTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _which_side_effect(self, present):
        def _which(name):
            return f"/usr/bin/{name}" if name in present else None
        return _which


class TestPreflightPass(PreflightTestCase):
    def test_passes_with_tk_remote_and_clean_tree(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertTrue(result.ok, result.failures)
        self.assertEqual(result.failures, [])

    def test_reports_remote_url_and_trunk_branch_on_pass(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertIsNotNone(result.remote_url)
        self.assertEqual(result.trunk_branch, "main")

    def test_passes_with_authenticated_gh_when_pr_creation_will_run(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh"})), \
             mock.patch.object(preflight, "_host_tool_authenticated", return_value=True):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertTrue(result.ok, result.failures)

    def test_reports_detected_host_tool_when_pr_creation_will_run(self):
        # Callers (the CLI's `create-pr` invocation) need to know which
        # tool preflight found, rather than re-detecting it themselves.
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh"})), \
             mock.patch.object(preflight, "_host_tool_authenticated", return_value=True):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertEqual(result.host_tool, "gh")

    def test_host_tool_is_none_when_pr_creation_will_not_run(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertIsNone(result.host_tool)

    def test_prefers_glab_for_gitlab_remote_when_both_tools_present(self):
        _init_repo_with_remote(self.repo_root)
        _run(["git", "remote", "set-url", "origin", "git@gitlab.com:org/repo.git"], self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh", "glab"})), \
             mock.patch.object(preflight, "_host_tool_authenticated", return_value=True):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertEqual(result.host_tool, "glab")

    def test_prefers_gh_for_github_remote_when_both_tools_present(self):
        _init_repo_with_remote(self.repo_root)
        _run(["git", "remote", "set-url", "origin", "https://github.com/org/repo.git"], self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh", "glab"})), \
             mock.patch.object(preflight, "_host_tool_authenticated", return_value=True):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertEqual(result.host_tool, "gh")

    def test_falls_back_to_path_order_when_remote_host_unrecognized(self):
        _init_repo_with_remote(self.repo_root)  # bare-dir remote, no github/gitlab host to match
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh", "glab"})), \
             mock.patch.object(preflight, "_host_tool_authenticated", return_value=True):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertEqual(result.host_tool, "gh")


class TestPreflightFailures(PreflightTestCase):
    def test_fails_when_tk_missing(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect(set())):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertFalse(result.ok)
        self.assertTrue(any("tk" in f for f in result.failures))

    def test_fails_when_no_remote_configured(self):
        _init_repo_with_remote(self.repo_root, with_remote=False)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertFalse(result.ok)
        self.assertTrue(any("remote" in f for f in result.failures))

    def test_fails_when_working_tree_dirty_and_lists_paths(self):
        _init_repo_with_remote(self.repo_root)
        (self.repo_root / "dirty.txt").write_text("uncommitted\n")
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertFalse(result.ok)
        self.assertTrue(any("dirty.txt" in f for f in result.failures))

    def test_fails_when_gh_unauthenticated_and_pr_creation_will_run(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh"})), \
             mock.patch.object(preflight, "_host_tool_authenticated", return_value=False):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("gh" in f and "auth" in f for f in result.failures))

    def test_fails_when_gitlab_remote_but_only_gh_on_path(self):
        # glab is required for this origin host — falling back to gh would
        # run `gh pr create` against a repo gh has no relationship to.
        _init_repo_with_remote(self.repo_root)
        _run(["git", "remote", "set-url", "origin", "git@gitlab.com:org/repo.git"], self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "gh"})), \
             mock.patch.object(preflight, "_host_tool_authenticated") as mock_auth:
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("glab" in f and "PATH" in f for f in result.failures))
        mock_auth.assert_not_called()

    def test_fails_when_github_remote_but_only_glab_on_path(self):
        _init_repo_with_remote(self.repo_root)
        _run(["git", "remote", "set-url", "origin", "https://github.com/org/repo.git"], self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk", "glab"})), \
             mock.patch.object(preflight, "_host_tool_authenticated") as mock_auth:
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("gh" in f and "PATH" in f for f in result.failures))
        mock_auth.assert_not_called()

    def test_fails_when_neither_gh_nor_glab_found_and_pr_creation_will_run(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("gh" in f or "glab" in f for f in result.failures))

    def test_skips_host_tool_check_when_pr_creation_will_not_run(self):
        _init_repo_with_remote(self.repo_root)
        with mock.patch.object(preflight.shutil, "which", side_effect=self._which_side_effect({"tk"})):
            result = preflight.run_preflight(self.repo_root, will_create_prs=False)
        self.assertTrue(result.ok, result.failures)


if __name__ == "__main__":
    unittest.main()
