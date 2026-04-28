"""Tests for the yapermission rule engine.

Run from the plugin root:
    python3 -m unittest discover plugins/yapermission/tests

Run a single class:
    python3 -m unittest plugins.yapermission.tests.test_yapermission.TestRuleMatches
"""
# pyright: reportAttributeAccessIssue=false
# Pyright can't statically resolve the sys.path.insert below — at runtime the
# tests import scripts/yapermission.py just fine.
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Make `scripts/yapermission.py` importable without packaging gymnastics.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import yapermission as yp  # noqa: E402


class TestRuleMatches(unittest.TestCase):
    def test_tool_mismatch_returns_false(self):
        rule = {"tool": "Bash", "matches": [{}]}
        self.assertFalse(yp.rule_matches(rule, "Edit", {"file_path": "/x"}))

    def test_missing_matches_returns_true(self):
        rule = {"tool": "Bash"}
        self.assertTrue(yp.rule_matches(rule, "Bash", {"command": "anything"}))

    def test_empty_matches_list_returns_true(self):
        rule = {"tool": "Bash", "matches": []}
        self.assertTrue(yp.rule_matches(rule, "Bash", {"command": "anything"}))

    def test_empty_match_entry_matches_any_input(self):
        rule = {"tool": "Bash", "matches": [{}]}
        self.assertTrue(yp.rule_matches(rule, "Bash", {"command": "git status"}))
        self.assertTrue(yp.rule_matches(rule, "Bash", {}))

    def test_single_field_match(self):
        rule = {"tool": "Bash", "matches": [{"command": "^git status"}]}
        self.assertTrue(yp.rule_matches(rule, "Bash", {"command": "git status -sb"}))

    def test_single_field_mismatch(self):
        rule = {"tool": "Bash", "matches": [{"command": "^git status"}]}
        self.assertFalse(yp.rule_matches(rule, "Bash", {"command": "rm -rf /"}))

    def test_or_across_entries_second_matches(self):
        rule = {
            "tool": "Bash",
            "matches": [{"command": "^git"}, {"command": "^ls"}],
        }
        self.assertTrue(yp.rule_matches(rule, "Bash", {"command": "ls -la"}))

    def test_or_across_entries_none_match(self):
        rule = {
            "tool": "Bash",
            "matches": [{"command": "^git"}, {"command": "^ls"}],
        }
        self.assertFalse(yp.rule_matches(rule, "Bash", {"command": "rm -rf /"}))

    def test_and_within_entry_one_field_fails(self):
        rule = {
            "tool": "Edit",
            "matches": [{"file_path": "^/etc/", "old_string": "important"}],
        }
        self.assertFalse(
            yp.rule_matches(
                rule, "Edit", {"file_path": "/etc/hosts", "old_string": "trivial"}
            )
        )

    def test_and_within_entry_all_fields_match(self):
        rule = {
            "tool": "Edit",
            "matches": [{"file_path": "^/etc/", "old_string": "important"}],
        }
        self.assertTrue(
            yp.rule_matches(
                rule, "Edit", {"file_path": "/etc/hosts", "old_string": "important config"}
            )
        )

    def test_missing_field_treated_as_empty_string(self):
        rule = {"tool": "Bash", "matches": [{"command": "^git"}]}
        self.assertFalse(yp.rule_matches(rule, "Bash", {}))

        # Patterns that match the empty string still fire.
        rule_loose = {"tool": "Bash", "matches": [{"command": ".*"}]}
        self.assertTrue(yp.rule_matches(rule_loose, "Bash", {}))

    def test_tool_regex_alternation(self):
        rule = {"tool": "Write|Edit", "matches": [{}]}
        self.assertTrue(yp.rule_matches(rule, "Write", {"file_path": "/x"}))
        self.assertTrue(yp.rule_matches(rule, "Edit", {"file_path": "/x"}))
        self.assertFalse(yp.rule_matches(rule, "Read", {"file_path": "/x"}))

    def test_tool_regex_mcp_namespace(self):
        rule = {"tool": "^mcp__github__(get_|list_)", "matches": [{}]}
        self.assertTrue(yp.rule_matches(rule, "mcp__github__list_issues", {}))
        self.assertTrue(yp.rule_matches(rule, "mcp__github__get_issue", {}))
        self.assertFalse(yp.rule_matches(rule, "mcp__github__create_issue", {}))


class TestDecide(unittest.TestCase):
    def test_empty_config_returns_ask(self):
        decision = yp.decide({}, "Bash", {"command": "git status"})
        self.assertEqual(decision.permission, "ask")
        self.assertIsNone(decision.rule_name)

    def test_default_approve_returns_allow_when_no_rules_match(self):
        decision = yp.decide({"default": "approve"}, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "allow")

    def test_default_block_returns_deny_when_no_rules_match(self):
        decision = yp.decide({"default": "block"}, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "deny")

    def test_default_unknown_falls_back_to_ask(self):
        decision = yp.decide({"default": "nonsense"}, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "ask")

    def test_deny_rule_match_returns_deny_with_reason(self):
        config = {
            "deny": [
                {
                    "name": "nuke",
                    "tool": "Bash",
                    "matches": [{"command": "rm -rf"}],
                    "reason": "destructive",
                }
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "rm -rf /tmp/x"})
        self.assertEqual(decision.permission, "deny")
        self.assertEqual(decision.rule_name, "nuke")
        self.assertEqual(decision.reason, "destructive")

    def test_deny_without_reason_gets_generic_message(self):
        config = {"deny": [{"tool": "Bash", "matches": [{}]}]}
        decision = yp.decide(config, "Bash", {"command": "anything"})
        self.assertEqual(decision.permission, "deny")
        self.assertIn("yapermission", decision.reason.lower())

    def test_approve_rule_match_returns_allow(self):
        config = {
            "approve": [
                {"name": "ok", "tool": "Bash", "matches": [{"command": "^git"}]}
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "git status"})
        self.assertEqual(decision.permission, "allow")
        self.assertEqual(decision.rule_name, "ok")

    def test_deny_wins_when_both_deny_and_approve_match(self):
        config = {
            "deny": [{"name": "blocked", "tool": "Bash", "matches": [{}]}],
            "approve": [{"name": "allowed", "tool": "Bash", "matches": [{}]}],
        }
        decision = yp.decide(config, "Bash", {"command": "git status"})
        self.assertEqual(decision.permission, "deny")
        self.assertEqual(decision.rule_name, "blocked")

    def test_first_matching_rule_wins_within_group(self):
        config = {
            "approve": [
                {"name": "first", "tool": "Bash", "matches": [{"command": "^git"}]},
                {"name": "second", "tool": "Bash", "matches": [{"command": "^git"}]},
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "git status"})
        self.assertEqual(decision.rule_name, "first")

    def test_falls_through_to_default_when_no_rule_matches(self):
        config = {
            "default": "block",
            "approve": [{"name": "nope", "tool": "Edit", "matches": [{}]}],
        }
        decision = yp.decide(config, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "deny")


class TestNormalizeDefault(unittest.TestCase):
    def test_normalization_table(self):
        cases = {
            "approve": "allow",
            "allow": "allow",
            "block": "deny",
            "deny": "deny",
            "ask": "ask",
            "nonsense": "ask",
            "": "ask",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(yp._normalize_default(raw), expected)


class TestActiveConfigPath(unittest.TestCase):
    def setUp(self):
        self._original_global = yp.GLOBAL_CONFIG
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        # Redirect global config to a tmp location so tests don't touch ~/.
        yp.GLOBAL_CONFIG = self.tmp / "global" / ".yapermission.yaml"

    def tearDown(self):
        yp.GLOBAL_CONFIG = self._original_global

    def test_project_config_wins_over_global(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()
        project_cfg = project_dir / yp.PROJECT_CONFIG_NAME
        project_cfg.write_text("default: approve\n")

        yp.GLOBAL_CONFIG.parent.mkdir()
        yp.GLOBAL_CONFIG.write_text("default: block\n")

        self.assertEqual(yp.active_config_path(str(project_dir)), project_cfg)

    def test_falls_back_to_global_when_no_project(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()

        yp.GLOBAL_CONFIG.parent.mkdir()
        yp.GLOBAL_CONFIG.write_text("default: ask\n")

        self.assertEqual(yp.active_config_path(str(project_dir)), yp.GLOBAL_CONFIG)

    def test_returns_none_when_neither_exists(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()

        self.assertIsNone(yp.active_config_path(str(project_dir)))


if __name__ == "__main__":
    unittest.main()
