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

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_default_allow_returns_allow_when_no_rules_match(self):
        decision = yp.decide({"default": "allow"}, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "allow")

    def test_default_deny_returns_deny_when_no_rules_match(self):
        decision = yp.decide({"default": "deny"}, "Bash", {"command": "x"})
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

    def test_allow_rule_match_returns_allow(self):
        config = {
            "allow": [
                {"name": "ok", "tool": "Bash", "matches": [{"command": "^git"}]}
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "git status"})
        self.assertEqual(decision.permission, "allow")
        self.assertEqual(decision.rule_name, "ok")

    def test_ask_rule_match_returns_ask_with_reason(self):
        config = {
            "ask": [
                {
                    "name": "force-push-prompt",
                    "tool": "Bash",
                    "matches": [{"command": "push.*--force"}],
                    "reason": "Force-push deserves a manual confirm",
                }
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "git push --force"})
        self.assertEqual(decision.permission, "ask")
        self.assertEqual(decision.reason, "Force-push deserves a manual confirm")

    def test_defer_rule_match_returns_defer(self):
        config = {
            "defer": [
                {"name": "let-next-hook-decide", "tool": "Bash", "matches": [{}]}
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "anything"})
        self.assertEqual(decision.permission, "defer")
        self.assertEqual(decision.rule_name, "let-next-hook-decide")

    def test_eval_order_deny_beats_ask(self):
        config = {
            "deny": [{"name": "blocked", "tool": "Bash", "matches": [{}]}],
            "ask": [{"name": "would-prompt", "tool": "Bash", "matches": [{}]}],
        }
        decision = yp.decide(config, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "deny")
        self.assertEqual(decision.rule_name, "blocked")

    def test_eval_order_ask_beats_allow(self):
        config = {
            "ask": [{"name": "prompt-me", "tool": "Bash", "matches": [{}]}],
            "allow": [{"name": "auto-allow", "tool": "Bash", "matches": [{}]}],
        }
        decision = yp.decide(config, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "ask")
        self.assertEqual(decision.rule_name, "prompt-me")

    def test_eval_order_allow_beats_defer(self):
        config = {
            "allow": [{"name": "auto-allow", "tool": "Bash", "matches": [{}]}],
            "defer": [{"name": "next-hook", "tool": "Bash", "matches": [{}]}],
        }
        decision = yp.decide(config, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "allow")
        self.assertEqual(decision.rule_name, "auto-allow")

    def test_first_matching_rule_wins_within_group(self):
        config = {
            "allow": [
                {"name": "first", "tool": "Bash", "matches": [{"command": "^git"}]},
                {"name": "second", "tool": "Bash", "matches": [{"command": "^git"}]},
            ]
        }
        decision = yp.decide(config, "Bash", {"command": "git status"})
        self.assertEqual(decision.rule_name, "first")

    def test_falls_through_to_default_when_no_rule_matches(self):
        config = {
            "default": "deny",
            "allow": [{"name": "nope", "tool": "Edit", "matches": [{}]}],
        }
        decision = yp.decide(config, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "deny")

    # -- Cache-aware ask rules -------------------------------------------

    def _cacheable_ask_config(self, reason=None):
        rule = {
            "name": "deploy",
            "tool": "Bash",
            "matches": [{"command": "^deploy"}],
            "cacheable": True,
        }
        if reason is not None:
            rule["reason"] = reason
        return {"ask": [rule]}

    def test_cacheable_ask_rule_without_matching_cache_entry_still_asks(self):
        # Regression guard: a cacheable rule must not short-circuit to allow
        # on its first, unapproved match.
        decision = yp.decide(
            self._cacheable_ask_config(), "Bash", {"command": "deploy prod"}, cache={}
        )
        self.assertEqual(decision.permission, "ask")
        self.assertEqual(decision.rule_name, "deploy")

    def test_cacheable_ask_rule_cache_hit_resolves_to_allow(self):
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            self._cacheable_ask_config(),
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
        )
        self.assertEqual(decision.permission, "allow")
        self.assertEqual(decision.rule_name, "deploy")
        self.assertEqual(decision.source, "cache")

    def test_deny_rule_beats_a_matching_cache_entry(self):
        config = self._cacheable_ask_config()
        config["deny"] = [{"name": "blocked", "tool": "Bash", "matches": [{}]}]
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
        )
        self.assertEqual(decision.permission, "deny")
        self.assertEqual(decision.rule_name, "blocked")

    def test_non_cacheable_ask_rule_ignores_stale_cache_entry(self):
        config = {
            "ask": [
                {"name": "deploy", "tool": "Bash", "matches": [{"command": "^deploy"}]}
            ]
        }
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
        )
        self.assertEqual(decision.permission, "ask")
        self.assertIsNone(decision.additional_context)

    def test_cache_entry_stops_hitting_once_rule_loses_cacheable_flag(self):
        config = {
            "ask": [
                {"name": "deploy", "tool": "Bash", "matches": [{"command": "^deploy"}]}
            ]
        }
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
        )
        self.assertEqual(decision.permission, "ask")
        self.assertEqual(decision.rule_name, "deploy")

    def test_cache_entry_stops_hitting_once_rule_removed_from_config(self):
        config = {"default": "deny", "ask": []}
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
        )
        # No rule matches at all now, so evaluation falls through to the
        # top-level default rather than granting a stray cache hit.
        self.assertEqual(decision.permission, "deny")
        self.assertIsNone(decision.rule_name)

    def test_cacheable_ask_rule_sets_additional_context_and_keeps_reason_plain(self):
        config = self._cacheable_ask_config(reason="Deploys need a human look")
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache={},
            session_id="S1",
        )
        self.assertEqual(decision.permission, "ask")
        self.assertEqual(decision.reason, "Deploys need a human look")
        self.assertIsNotNone(decision.additional_context)
        self.assertIn("S1", decision.additional_context)
        self.assertIn("cacheable", decision.additional_context.lower())
        self.assertNotIn("Deploys need a human look", decision.additional_context)
        self.assertNotIn("S1", decision.reason)

    def test_cacheable_ask_rule_without_session_id_sets_no_additional_context(self):
        # A missing session_id must never render into the cue: it would
        # invite a `remember` call keyed to "" that the cache read path
        # (cmd_hook's empty-session_id guard) can never look up again.
        decision = yp.decide(
            self._cacheable_ask_config(), "Bash", {"command": "deploy prod"}, cache={}
        )
        self.assertEqual(decision.permission, "ask")
        self.assertIsNone(decision.additional_context)


class TestNormalizeDefault(unittest.TestCase):
    def test_normalization_table(self):
        cases = {
            # The four valid permissionDecision values pass through unchanged.
            "allow": "allow",
            "deny": "deny",
            "ask": "ask",
            "defer": "defer",
            # Anything else falls back to ask (fail-open).
            "approve": "ask",
            "block": "ask",
            "nonsense": "ask",
            "": "ask",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(yp._normalize_default(raw), expected)


class TestDeferDefault(unittest.TestCase):
    def test_default_defer_returns_defer_when_no_rules_match(self):
        decision = yp.decide({"default": "defer"}, "Bash", {"command": "x"})
        self.assertEqual(decision.permission, "defer")
        self.assertIsNone(decision.rule_name)


class TestActiveConfigPath(unittest.TestCase):
    def setUp(self):
        self._original_global = yp.GLOBAL_CONFIG
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        # Redirect global config to a tmp location so tests don't touch ~/.
        yp.GLOBAL_CONFIG = self.tmp / "global" / ".yapermission.toml"

    def tearDown(self):
        yp.GLOBAL_CONFIG = self._original_global

    def test_project_config_wins_over_global(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()
        project_cfg = project_dir / yp.PROJECT_CONFIG_NAME
        project_cfg.write_text('default = "allow"\n')

        yp.GLOBAL_CONFIG.parent.mkdir()
        yp.GLOBAL_CONFIG.write_text('default = "deny"\n')

        self.assertEqual(yp.active_config_path(str(project_dir)), project_cfg)

    def test_falls_back_to_global_when_no_project(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()

        yp.GLOBAL_CONFIG.parent.mkdir()
        yp.GLOBAL_CONFIG.write_text('default = "ask"\n')

        self.assertEqual(yp.active_config_path(str(project_dir)), yp.GLOBAL_CONFIG)

    def test_returns_none_when_neither_exists(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()

        self.assertIsNone(yp.active_config_path(str(project_dir)))


class TestCacheStore(unittest.TestCase):
    def setUp(self):
        self._original_cache_path = yp.CACHE_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        # Redirect the cache to a tmp location so tests don't touch the real
        # OS temp dir, mirroring TestActiveConfigPath's GLOBAL_CONFIG swap.
        yp.CACHE_PATH = self.tmp / "yapermission-cache.jsonl"

    def tearDown(self):
        yp.CACHE_PATH = self._original_cache_path

    def test_round_trip(self):
        yp.append_cache_entry("S1", "my-rule", "Bash", {"command": "git push"}, "/cfg.toml")

        cache = yp.load_cache("S1")

        key = yp.cache_key("my-rule", "Bash", {"command": "git push"}, "/cfg.toml")
        self.assertIn(key, cache)
        self.assertEqual(cache[key]["rule_name"], "my-rule")
        self.assertEqual(cache[key]["tool_name"], "Bash")
        self.assertEqual(cache[key]["tool_input"], {"command": "git push"})

    def test_cross_session_miss(self):
        yp.append_cache_entry("S1", "my-rule", "Bash", {"command": "git push"}, "/cfg.toml")

        self.assertEqual(yp.load_cache("S2"), {})

    def test_missing_cache_file_returns_empty_dict(self):
        self.assertEqual(yp.load_cache("S1"), {})

    def test_load_cache_skips_corrupt_and_non_object_lines(self):
        yp.append_cache_entry("S1", "rule-a", "Bash", {"command": "a"}, "/cfg.toml")
        with yp.CACHE_PATH.open("a") as f:
            f.write("not valid json\n")
            f.write("[1, 2]\n")  # valid JSON, but not a record object
        yp.append_cache_entry("S1", "rule-b", "Bash", {"command": "b"}, "/cfg.toml")

        cache = yp.load_cache("S1")

        self.assertEqual(len(cache), 2)

    def test_cache_key_accepts_path_or_str_config_path_equivalently(self):
        # active_config_path() returns a Path; stored records round-trip
        # through str(). Both must resolve to the same key.
        k_path = yp.cache_key("r", "Bash", {"command": "x"}, Path("/a/b/.yapermission.toml"))
        k_str = yp.cache_key("r", "Bash", {"command": "x"}, "/a/b/.yapermission.toml")
        self.assertEqual(k_path, k_str)

    def test_cache_key_is_stable_regardless_of_field_insertion_order(self):
        k1 = yp.cache_key("r", "Bash", {"a": "1", "b": "2"}, "/cfg.toml")
        k2 = yp.cache_key("r", "Bash", {"b": "2", "a": "1"}, "/cfg.toml")
        self.assertEqual(k1, k2)

    def test_append_creates_file_with_0600_permissions(self):
        yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml")

        mode = yp.CACHE_PATH.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_cache_key_differs_for_naive_concatenation_collision(self):
        # "1"+"23" and "12"+"3" would collide under naive string concatenation.
        k1 = yp.cache_key("r", "Bash", {"a": "1", "b": "23"}, "/cfg.toml")
        k2 = yp.cache_key("r", "Bash", {"a": "12", "b": "3"}, "/cfg.toml")
        self.assertNotEqual(k1, k2)

    def test_cache_key_differs_for_swapped_field_values(self):
        # Same values, swapped across keys — a naive per-value join wouldn't
        # necessarily distinguish which field order produced the string.
        k1 = yp.cache_key("r", "Bash", {"command": "foo", "path": "bar"}, "/cfg.toml")
        k2 = yp.cache_key("r", "Bash", {"command": "bar", "path": "foo"}, "/cfg.toml")
        self.assertNotEqual(k1, k2)

    def test_cache_key_differs_for_config_path(self):
        k1 = yp.cache_key("r", "Bash", {"command": "x"}, "/project-a/.yapermission.toml")
        k2 = yp.cache_key("r", "Bash", {"command": "x"}, "/project-b/.yapermission.toml")
        self.assertNotEqual(k1, k2)

    def test_append_refuses_when_cache_path_is_symlink(self):
        target = self.tmp / "target.jsonl"
        target.write_text("")
        link = self.tmp / "link.jsonl"
        link.symlink_to(target)
        yp.CACHE_PATH = link

        yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml")

        self.assertEqual(target.read_text(), "")

    def test_append_refuses_when_owning_uid_mismatches(self):
        class _WrongOwner:
            st_uid = os.getuid() + 1

        with mock.patch("yapermission.os.fstat", return_value=_WrongOwner()):
            yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml")

        self.assertEqual(yp.load_cache("S1"), {})

    def test_load_cache_fails_open_when_cache_path_is_symlink(self):
        target = self.tmp / "target.jsonl"
        target.write_text(
            json.dumps(
                {
                    "session_id": "S1",
                    "rule_name": "r",
                    "tool_name": "Bash",
                    "tool_input": {"command": "x"},
                    "config_path": "/cfg.toml",
                }
            )
            + "\n"
        )
        link = self.tmp / "link.jsonl"
        link.symlink_to(target)
        yp.CACHE_PATH = link

        self.assertEqual(yp.load_cache("S1"), {})

    def test_load_cache_fails_open_when_owning_uid_mismatches(self):
        yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml")

        class _WrongOwner:
            st_uid = os.getuid() + 1

        with mock.patch("yapermission.os.fstat", return_value=_WrongOwner()):
            cache = yp.load_cache("S1")

        self.assertEqual(cache, {})


class TestEmitHookOutput(unittest.TestCase):
    def _capture(self, decision):
        buf = io.StringIO()
        with mock.patch("yapermission.sys.stdout", buf):
            yp.emit_hook_output(decision)
        return json.loads(buf.getvalue())

    def test_additional_context_and_reason_land_in_separate_fields(self):
        decision = yp.Decision(
            permission="ask",
            reason="human-facing reason",
            additional_context="agent-facing cue (session_id=S1)",
        )
        out = self._capture(decision)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecisionReason"], "human-facing reason")
        self.assertEqual(out["additionalContext"], "agent-facing cue (session_id=S1)")
        self.assertNotEqual(out["permissionDecisionReason"], out["additionalContext"])

    def test_additional_context_omitted_when_absent(self):
        decision = yp.Decision(permission="allow")
        out = self._capture(decision)["hookSpecificOutput"]
        self.assertNotIn("additionalContext", out)


class TestCmdHook(unittest.TestCase):
    def setUp(self):
        self._original_cache_path = yp.CACHE_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        yp.CACHE_PATH = self.tmp / "yapermission-cache.jsonl"

    def tearDown(self):
        yp.CACHE_PATH = self._original_cache_path

    def _run_hook(self, event):
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()
        with mock.patch("yapermission.sys.stdin", stdin), mock.patch(
            "yapermission.sys.stdout", stdout
        ), mock.patch("yapermission.log_decision") as mock_log:
            yp.cmd_hook()
        return json.loads(stdout.getvalue()), mock_log

    def _write_cacheable_ask_config(self, project_dir):
        config_path = project_dir / yp.PROJECT_CONFIG_NAME
        config_path.write_text(
            '[[ask]]\n'
            'name = "deploy"\n'
            'tool = "Bash"\n'
            'cacheable = true\n'
            'matches = [{ command = "^deploy" }]\n'
        )
        return config_path

    def test_cache_resolved_decision_logs_source_cache_and_rule_name(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()
        config_path = self._write_cacheable_ask_config(project_dir)
        yp.append_cache_entry(
            "S1", "deploy", "Bash", {"command": "deploy prod"}, str(config_path)
        )

        event = {
            "session_id": "S1",
            "tool_name": "Bash",
            "tool_input": {"command": "deploy prod"},
            "cwd": str(project_dir),
        }
        output, mock_log = self._run_hook(event)

        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "allow")
        record = mock_log.call_args[0][0]
        self.assertEqual(record["source"], "cache")
        self.assertEqual(record["rule"], "deploy")

    def test_first_hit_asks_and_logs_no_source_field(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()
        self._write_cacheable_ask_config(project_dir)

        event = {
            "session_id": "S1",
            "tool_name": "Bash",
            "tool_input": {"command": "deploy prod"},
            "cwd": str(project_dir),
        }
        output, mock_log = self._run_hook(event)

        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("additionalContext", output["hookSpecificOutput"])
        record = mock_log.call_args[0][0]
        self.assertNotIn("source", record)


if __name__ == "__main__":
    unittest.main()
