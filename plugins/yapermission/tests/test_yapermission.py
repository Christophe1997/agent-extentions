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
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

# Make `scripts/yapermission.py` importable without packaging gymnastics.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import yapermission as yp  # noqa: E402


def _cacheable_deploy_toml(*, named: bool = True, cacheable: bool = True) -> str:
    """TOML for a single `[[ask]]` "deploy" rule matching `^deploy` on Bash.

    The standard cacheable-ask fixture reused across TestCmdHook,
    TestCmdExplain, and TestRemember; `named=False` / `cacheable=False`
    produce the two variant configs some tests need in place of a
    hand-edited copy of the literal.
    """
    lines = ["[[ask]]\n"]
    if named:
        lines.append('name = "deploy"\n')
    lines.append('tool = "Bash"\n')
    if cacheable:
        lines.append("cacheable = true\n")
    lines.append('matches = [{ command = "^deploy" }]\n')
    return "".join(lines)


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
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml", "/repo")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            self._cacheable_ask_config(),
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
            cwd="/repo",
        )
        self.assertEqual(decision.permission, "allow")
        self.assertEqual(decision.rule_name, "deploy")
        self.assertEqual(decision.source, "cache")

    def test_deny_rule_beats_a_matching_cache_entry(self):
        config = self._cacheable_ask_config()
        config["deny"] = [{"name": "blocked", "tool": "Bash", "matches": [{}]}]
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml", "/repo")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
            cwd="/repo",
        )
        self.assertEqual(decision.permission, "deny")
        self.assertEqual(decision.rule_name, "blocked")

    def test_cache_entry_stops_hitting_once_rule_loses_cacheable_flag(self):
        # Also covers the non-cacheable-rule case: a rule with no `cacheable`
        # flag at all ignores a stale cache entry identically to one that
        # lost the flag — same config, same rule, same stale entry.
        config = {
            "ask": [
                {"name": "deploy", "tool": "Bash", "matches": [{"command": "^deploy"}]}
            ]
        }
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml", "/repo")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
            cwd="/repo",
        )
        self.assertEqual(decision.permission, "ask")
        self.assertEqual(decision.rule_name, "deploy")
        self.assertIsNone(decision.additional_context)

    def test_cache_entry_stops_hitting_once_rule_removed_from_config(self):
        config = {"default": "deny", "ask": []}
        key = yp.cache_key("deploy", "Bash", {"command": "deploy prod"}, "/cfg.toml", "/repo")
        cache = {key: {"rule_name": "deploy"}}
        decision = yp.decide(
            config,
            "Bash",
            {"command": "deploy prod"},
            cache=cache,
            config_path="/cfg.toml",
            cwd="/repo",
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
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        # Redirect global config to a tmp location so tests don't touch ~/.
        self.enterContext(
            mock.patch.object(yp, "GLOBAL_CONFIG", self.tmp / "global" / ".yapermission.toml")
        )

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
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        # Redirect the cache to a tmp location so tests don't touch the real
        # OS temp dir, mirroring TestActiveConfigPath's GLOBAL_CONFIG swap.
        self.enterContext(
            mock.patch.object(yp, "CACHE_PATH", self.tmp / "yapermission-cache.jsonl")
        )

    def test_round_trip(self):
        yp.append_cache_entry(
            "S1", "my-rule", "Bash", {"command": "git push"}, "/cfg.toml", "/repo"
        )

        cache = yp.load_cache("S1")

        key = yp.cache_key("my-rule", "Bash", {"command": "git push"}, "/cfg.toml", "/repo")
        self.assertIn(key, cache)
        self.assertEqual(cache[key]["rule_name"], "my-rule")
        self.assertEqual(cache[key]["tool_name"], "Bash")
        self.assertEqual(cache[key]["tool_input"], {"command": "git push"})

    def test_cross_session_miss(self):
        yp.append_cache_entry(
            "S1", "my-rule", "Bash", {"command": "git push"}, "/cfg.toml", "/repo"
        )

        self.assertEqual(yp.load_cache("S2"), {})

    def test_missing_cache_file_returns_empty_dict(self):
        self.assertEqual(yp.load_cache("S1"), {})

    def test_load_cache_skips_corrupt_and_non_object_lines(self):
        yp.append_cache_entry("S1", "rule-a", "Bash", {"command": "a"}, "/cfg.toml", "/repo")
        with yp.CACHE_PATH.open("a") as f:
            f.write("not valid json\n")
            f.write("[1, 2]\n")  # valid JSON, but not a record object
        yp.append_cache_entry("S1", "rule-b", "Bash", {"command": "b"}, "/cfg.toml", "/repo")

        cache = yp.load_cache("S1")

        self.assertEqual(len(cache), 2)

    def test_cache_key_accepts_path_or_str_config_path_equivalently(self):
        # active_config_path() returns a Path; stored records round-trip
        # through str(). Both must resolve to the same key.
        k_path = yp.cache_key(
            "r", "Bash", {"command": "x"}, Path("/a/b/.yapermission.toml"), "/repo"
        )
        k_str = yp.cache_key("r", "Bash", {"command": "x"}, "/a/b/.yapermission.toml", "/repo")
        self.assertEqual(k_path, k_str)

    def test_cache_key_is_stable_regardless_of_field_insertion_order(self):
        k1 = yp.cache_key("r", "Bash", {"a": "1", "b": "2"}, "/cfg.toml", "/repo")
        k2 = yp.cache_key("r", "Bash", {"b": "2", "a": "1"}, "/cfg.toml", "/repo")
        self.assertEqual(k1, k2)

    def test_append_creates_file_with_0600_permissions(self):
        yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo")

        mode = yp.CACHE_PATH.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_cache_key_differs_for_naive_concatenation_collision(self):
        # "1"+"23" and "12"+"3" would collide under naive string concatenation.
        k1 = yp.cache_key("r", "Bash", {"a": "1", "b": "23"}, "/cfg.toml", "/repo")
        k2 = yp.cache_key("r", "Bash", {"a": "12", "b": "3"}, "/cfg.toml", "/repo")
        self.assertNotEqual(k1, k2)

    def test_cache_key_differs_for_swapped_field_values(self):
        # Same values, swapped across keys — a naive per-value join wouldn't
        # necessarily distinguish which field order produced the string.
        k1 = yp.cache_key("r", "Bash", {"command": "foo", "path": "bar"}, "/cfg.toml", "/repo")
        k2 = yp.cache_key("r", "Bash", {"command": "bar", "path": "foo"}, "/cfg.toml", "/repo")
        self.assertNotEqual(k1, k2)

    def test_cache_key_differs_for_config_path(self):
        k1 = yp.cache_key(
            "r", "Bash", {"command": "x"}, "/project-a/.yapermission.toml", "/repo"
        )
        k2 = yp.cache_key(
            "r", "Bash", {"command": "x"}, "/project-b/.yapermission.toml", "/repo"
        )
        self.assertNotEqual(k1, k2)

    def test_cache_key_differs_for_cwd(self):
        # A shared (e.g. global) config_path must not let two different
        # calling directories collide onto the same cache key — the key
        # must scope on *where* the call ran, not just *which* config it
        # ran under.
        k1 = yp.cache_key("r", "Bash", {"command": "x"}, "/cfg.toml", "/project-a")
        k2 = yp.cache_key("r", "Bash", {"command": "x"}, "/cfg.toml", "/project-b")
        self.assertNotEqual(k1, k2)

    def test_append_refuses_when_cache_path_is_symlink(self):
        target = self.tmp / "target.jsonl"
        target.write_text("")
        link = self.tmp / "link.jsonl"
        link.symlink_to(target)
        yp.CACHE_PATH = link

        yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo")

        self.assertEqual(target.read_text(), "")

    def test_append_refuses_when_owning_uid_mismatches(self):
        class _WrongOwner:
            st_uid = os.getuid() + 1

        with mock.patch("yapermission.os.fstat", return_value=_WrongOwner()):
            yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo")

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
        yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo")

        class _WrongOwner:
            st_uid = os.getuid() + 1

        with mock.patch("yapermission.os.fstat", return_value=_WrongOwner()):
            cache = yp.load_cache("S1")

        self.assertEqual(cache, {})

    def _call_with_timeout(self, fn, *args, seconds=2, **kwargs):
        """Run `fn` bounded by a SIGALRM, so a pre-fix hang fails fast and
        observably instead of wedging the whole suite.

        Asserting on elapsed time (not just on the raised exception) is
        load-bearing: `TimeoutError` is itself an `OSError` subclass, so a
        hang that gets interrupted mid-`os.open()` is silently absorbed by
        yapermission's own `except OSError` handling — the call still
        returns its normal fail-open value, just ~`seconds` late. Only the
        elapsed-time check tells a genuine prompt return apart from a
        swallowed near-timeout.
        """

        def _on_alarm(signum, frame):
            raise TimeoutError(f"{fn.__name__} blocked past {seconds}s — likely hung on open()")

        old_handler = signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(seconds)
        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed, 1.0,
            f"{fn.__name__} took {elapsed:.3f}s — expected a prompt, non-blocking return",
        )
        return result

    def test_load_cache_does_not_hang_on_a_planted_fifo(self):
        # A FIFO pre-planted at CACHE_PATH (e.g. by another process racing
        # yapermission's first real write) must not block the read path
        # indefinitely — it must be rejected as "not a regular file".
        os.mkfifo(yp.CACHE_PATH)

        result = self._call_with_timeout(yp.load_cache, "S1")

        self.assertEqual(result, {})

    def test_append_cache_entry_does_not_hang_on_a_planted_fifo(self):
        os.mkfifo(yp.CACHE_PATH)

        result = self._call_with_timeout(
            yp.append_cache_entry, "S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo"
        )

        self.assertIs(result, False)

    def test_append_cache_entry_returns_true_on_success(self):
        self.assertIs(
            yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo"),
            True,
        )

    def test_append_cache_entry_returns_false_when_cache_path_is_symlink(self):
        target = self.tmp / "target.jsonl"
        target.write_text("")
        link = self.tmp / "link.jsonl"
        link.symlink_to(target)
        yp.CACHE_PATH = link

        self.assertIs(
            yp.append_cache_entry("S1", "rule", "Bash", {"command": "x"}, "/cfg.toml", "/repo"),
            False,
        )


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
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        self.enterContext(
            mock.patch.object(yp, "CACHE_PATH", self.tmp / "yapermission-cache.jsonl")
        )

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
        config_path.write_text(_cacheable_deploy_toml())
        return config_path

    def test_cache_resolved_decision_logs_source_cache_and_rule_name(self):
        project_dir = self.tmp / "project"
        project_dir.mkdir()
        config_path = self._write_cacheable_ask_config(project_dir)
        yp.append_cache_entry(
            "S1", "deploy", "Bash", {"command": "deploy prod"}, str(config_path), str(project_dir)
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


class TestCmdExplain(unittest.TestCase):
    """cmd_explain's optional --session flag and its cache-state line.

    cmd_explain has no session context of its own (it's a manual dry-run
    tool, not the hook reading a PreToolUse event) — see correction #2 in
    the U4 unit brief. These tests pin down the three honest states: a real
    cache hit, a checked-but-missing entry, and "not checked at all" when
    --session is omitted (never a guessed default).
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        self.enterContext(
            mock.patch.object(yp, "CACHE_PATH", self.tmp / "yapermission-cache.jsonl")
        )
        self.enterContext(
            mock.patch.object(yp, "GLOBAL_CONFIG", self.tmp / "global" / ".yapermission.toml")
        )
        self.project_dir = self.tmp / "project"
        self.project_dir.mkdir()

    def _write_cacheable_ask_config(self) -> Path:
        config_path = self.project_dir / yp.PROJECT_CONFIG_NAME
        config_path.write_text(_cacheable_deploy_toml())
        return config_path

    def _explain(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch(
            "yapermission.os.getcwd", return_value=str(self.project_dir)
        ), mock.patch("yapermission.sys.stdout", stdout), mock.patch(
            "yapermission.sys.stderr", stderr
        ):
            rc = yp.cmd_explain(argv)
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_session_given_with_cache_hit_reports_hit_alongside_trace(self):
        config_path = self._write_cacheable_ask_config()
        yp.append_cache_entry(
            "S1", "deploy", "Bash", {"command": "deploy prod"},
            str(config_path), str(self.project_dir),
        )

        rc, stdout, stderr = self._explain(
            ["--verbose", "--session", "S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertEqual(rc, 0)
        # The rule-level trace (from decide()) and the top-level cache-state
        # line must both show up — "alongside", not one replacing the other.
        self.assertIn("cache hit for rule 'deploy'", stdout)
        self.assertIn("cache:", stdout)
        self.assertIn("hit", stdout.lower())
        self.assertIn("S1", stdout)

    def test_session_given_with_no_matching_entry_reports_no_entry(self):
        self._write_cacheable_ask_config()

        rc, stdout, stderr = self._explain(
            ["--session", "S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertEqual(rc, 0)
        self.assertIn("cache:", stdout)
        self.assertIn("no matching cache entry", stdout.lower())
        self.assertNotIn("hit", stdout.lower())

    def test_session_omitted_reports_cache_state_not_checked(self):
        self._write_cacheable_ask_config()

        rc, stdout, stderr = self._explain(
            ["Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertEqual(rc, 0)
        self.assertIn("cache:", stdout)
        self.assertIn("not checked", stdout.lower())
        # Must not falsely imply a real lookup happened.
        self.assertNotIn("hit", stdout.lower())
        self.assertNotIn("no matching cache entry", stdout.lower())

    def test_session_given_but_no_active_config_reports_not_checked(self):
        # config_path is None here (no project or global config exists) —
        # no lookup was ever attempted, so the cache line must not claim a
        # real "no matching entry" result.
        rc, stdout, stderr = self._explain(
            ["--session", "S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertEqual(rc, 0)
        cache_line = next(line for line in stdout.splitlines() if line.startswith("cache:"))
        self.assertIn("not checked", cache_line.lower())
        self.assertNotIn("hit", cache_line.lower())
        self.assertNotIn("no matching cache entry", cache_line.lower())

    def test_session_given_but_config_load_fails_reports_not_checked(self):
        config_path = self.project_dir / yp.PROJECT_CONFIG_NAME
        config_path.write_text("this is not [valid toml\n")

        rc, stdout, stderr = self._explain(
            ["--session", "S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertEqual(rc, 0)
        cache_line = next(line for line in stdout.splitlines() if line.startswith("cache:"))
        self.assertIn("not checked", cache_line.lower())
        self.assertNotIn("hit", cache_line.lower())
        self.assertNotIn("no matching cache entry", cache_line.lower())

    def test_session_flag_missing_or_empty_value_exits_2(self):
        # A dangling flag and an explicit "" must both fail closed — an
        # empty session_id is falsy, so letting it through would silently
        # skip the cache lookup while still claiming one happened.
        for argv in (["--session"], ["--session", "", "Bash", "{}"]):
            with self.subTest(argv=argv):
                rc, stdout, stderr = self._explain(argv)
                self.assertEqual(rc, 2)
                self.assertTrue(stderr.strip())


class TestRemember(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        self.enterContext(
            mock.patch.object(yp, "CACHE_PATH", self.tmp / "yapermission-cache.jsonl")
        )
        # Redirect the global-config fallback too: a project dir with no
        # project-level .yapermission.toml would otherwise fall through to
        # the developer's real ~/.yapermission.toml (mirrors
        # TestActiveConfigPath's swap).
        self.enterContext(
            mock.patch.object(yp, "GLOBAL_CONFIG", self.tmp / "global" / ".yapermission.toml")
        )
        self.project_dir = self.tmp / "project"
        self.project_dir.mkdir()

    def _write_config(self, toml_text: str) -> Path:
        config_path = self.project_dir / yp.PROJECT_CONFIG_NAME
        config_path.write_text(toml_text)
        return config_path

    def _remember(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch(
            "yapermission.os.getcwd", return_value=str(self.project_dir)
        ), mock.patch("yapermission.sys.stdout", stdout), mock.patch(
            "yapermission.sys.stderr", stderr
        ), mock.patch("yapermission.log_decision") as mock_log:
            rc = yp.cmd_remember(argv)
        return rc, stdout.getvalue(), stderr.getvalue(), mock_log

    def test_successful_remember_persists_cache_entry_and_logs_grant(self):
        config_path = self._write_config(_cacheable_deploy_toml())

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertEqual(rc, 0)
        self.assertIn("deploy", stdout)

        cache = yp.load_cache("S1")
        key = yp.cache_key(
            "deploy", "Bash", {"command": "deploy prod"}, config_path, str(self.project_dir)
        )
        self.assertIn(key, cache)
        self.assertEqual(cache[key]["rule_name"], "deploy")

        record = mock_log.call_args[0][0]
        self.assertEqual(record["event"], "remember-granted")
        self.assertEqual(record["rule"], "deploy")
        self.assertEqual(record["session_id"], "S1")

    def test_failed_cache_write_refuses_instead_of_reporting_success(self):
        # append_cache_entry can silently fail (symlinked/wrong-owner cache
        # path, OSError). cmd_remember must not report "remembered" or log
        # a grant when the write never actually landed.
        self._write_config(_cacheable_deploy_toml())

        with mock.patch("yapermission.append_cache_entry", return_value=False):
            rc, stdout, stderr, mock_log = self._remember(
                ["S1", "Bash", json.dumps({"command": "deploy prod"})]
            )

        self.assertNotEqual(rc, 0)
        self.assertNotIn("remembered:", stdout)
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_deny_preempts_refuses_and_logs_refusal(self):
        # A matching cacheable [[ask]] rule is present too, so this proves
        # deny preempts rather than merely proving no ask rule exists.
        self._write_config(
            '[[deny]]\n'
            'name = "blocked"\n'
            'tool = "Bash"\n'
            'matches = [{ command = "^deploy" }]\n'
            '\n'
            + _cacheable_deploy_toml()
        )

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        record = mock_log.call_args[0][0]
        self.assertEqual(record["event"], "remember-refused")
        self.assertEqual(record["session_id"], "S1")

    def test_allow_only_refuses(self):
        # No ask rule matches this input at all — ask beats allow, so an
        # ask-rule match here would preempt allow and invalidate the case.
        self._write_config(
            '[[allow]]\n'
            'name = "auto"\n'
            'tool = "Bash"\n'
            'matches = [{ command = "^deploy" }]\n'
        )

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_defer_only_refuses(self):
        self._write_config(
            '[[defer]]\n'
            'name = "next-hook"\n'
            'tool = "Bash"\n'
            'matches = [{ command = "^deploy" }]\n'
        )

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_ask_rule_not_cacheable_refuses(self):
        self._write_config(_cacheable_deploy_toml(cacheable=False))

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_unnamed_cacheable_rule_refuses(self):
        # `name` is only "recommended" in the schema — an unnamed cacheable
        # rule must not be granted, since it would cache under
        # rule_name=None and collapse onto any other unnamed cacheable rule.
        self._write_config(_cacheable_deploy_toml(named=False))

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_duplicate_rule_name_gates_on_matched_object_not_name_lookup(self):
        # Two [[ask]] rules share the name "deploy": the earlier one is
        # cacheable but doesn't match this input, the later one matches but
        # isn't cacheable. A by-name lookup for "cacheable" would find the
        # earlier rule and grant incorrectly — remember must gate on the
        # rule object decide() actually matched, not on the matched name.
        self._write_config(
            '[[ask]]\n'
            'name = "deploy"\n'
            'tool = "Bash"\n'
            'cacheable = true\n'
            'matches = [{ command = "^deploy-other" }]\n'
            '\n'
            '[[ask]]\n'
            'name = "deploy"\n'
            'tool = "Bash"\n'
            'matches = [{ command = "^deploy" }]\n'
        )

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})

    def test_no_rule_matches_refuses_with_clear_message(self):
        self._write_config(_cacheable_deploy_toml())

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "rm -rf /"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        self.assertTrue(stderr.strip())
        record = mock_log.call_args[0][0]
        self.assertEqual(record["event"], "remember-refused")
        self.assertIsNone(record["rule"])

    def test_empty_session_id_refuses(self):
        # An entry stored under "" could never be looked up again by
        # cmd_hook's empty-session_id guard — refuse before writing it.
        self._write_config(_cacheable_deploy_toml())

        rc, stdout, stderr, mock_log = self._remember(
            ["", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache(""), {})
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_no_active_config_refuses(self):
        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})

    def test_config_load_failure_refuses(self):
        # Deliberate divergence from cmd_explain's fail-open-to-ask: a
        # revalidation gate that can't be evaluated must refuse, not allow.
        self._write_config("this is not [valid toml\n")

        rc, stdout, stderr, mock_log = self._remember(
            ["S1", "Bash", json.dumps({"command": "deploy prod"})]
        )

        self.assertNotEqual(rc, 0)
        self.assertEqual(yp.load_cache("S1"), {})
        self.assertEqual(mock_log.call_args[0][0]["event"], "remember-refused")

    def test_bad_usage_wrong_arg_count_exits_2(self):
        for argv in ([], ["S1"], ["S1", "Bash"], ["S1", "Bash", "{}", "extra"]):
            with self.subTest(argv=argv):
                rc, stdout, stderr, mock_log = self._remember(argv)
                self.assertEqual(rc, 2)
                self.assertIn("usage:", stderr)
                mock_log.assert_not_called()

    def test_invalid_tool_input_json_exits_2(self):
        rc, stdout, stderr, mock_log = self._remember(["S1", "Bash", "{not valid json"])

        self.assertEqual(rc, 2)
        mock_log.assert_not_called()

    def test_non_dict_tool_input_exits_2(self):
        # A valid-JSON, non-object payload (e.g. a bare list or string) would
        # otherwise reach rule_matches()'s tool_input.get(...) and traceback
        # instead of refusing cleanly. A config with a matching-tool rule is
        # required so evaluation actually reaches rule_matches() rather than
        # short-circuiting on "no active config" first.
        self._write_config(_cacheable_deploy_toml())
        for payload in ("[1, 2]", '"deploy prod"'):
            with self.subTest(payload=payload):
                rc, stdout, stderr, mock_log = self._remember(["S1", "Bash", payload])
                self.assertEqual(rc, 2)
                mock_log.assert_not_called()

    def test_remembered_call_resolves_to_allow_on_the_next_hook_run(self):
        # The store-level round trip (asserted elsewhere) only proves
        # cache_key is deterministic. This chains remember -> hook through
        # the real entry points to prove the requirement R2 actually makes:
        # a remembered call stops asking on a subsequent PreToolUse.
        self._write_config(_cacheable_deploy_toml())
        tool_input = {"command": "deploy prod"}

        rc, *_ = self._remember(["S1", "Bash", json.dumps(tool_input)])
        self.assertEqual(rc, 0)

        event = {
            "session_id": "S1",
            "tool_name": "Bash",
            "tool_input": tool_input,
            "cwd": str(self.project_dir),
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()
        with mock.patch("yapermission.sys.stdin", stdin), mock.patch(
            "yapermission.sys.stdout", stdout
        ), mock.patch("yapermission.log_decision") as mock_log:
            yp.cmd_hook()
        output = json.loads(stdout.getvalue())

        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "allow")
        record = mock_log.call_args[0][0]
        self.assertEqual(record["source"], "cache")
        self.assertEqual(record["rule"], "deploy")

    def test_remembered_call_does_not_hit_cache_from_a_different_cwd(self):
        # Regression guard for the global-config cross-project bleed: two
        # directories sharing the same (global) config_path, same rule, and
        # the identical tool_input must NOT share a cache entry — only the
        # directory the human actually approved from should get the hit.
        yp.GLOBAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        yp.GLOBAL_CONFIG.write_text(_cacheable_deploy_toml())
        tool_input = {"command": "deploy prod"}

        rc, *_ = self._remember(["S1", "Bash", json.dumps(tool_input)])
        self.assertEqual(rc, 0)

        other_dir = self.tmp / "other-project"
        other_dir.mkdir()
        event = {
            "session_id": "S1",
            "tool_name": "Bash",
            "tool_input": tool_input,
            "cwd": str(other_dir),
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()
        with mock.patch("yapermission.sys.stdin", stdin), mock.patch(
            "yapermission.sys.stdout", stdout
        ), mock.patch("yapermission.log_decision") as mock_log:
            yp.cmd_hook()
        output = json.loads(stdout.getvalue())

        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")
        record = mock_log.call_args[0][0]
        self.assertNotIn("source", record)


if __name__ == "__main__":
    unittest.main()
