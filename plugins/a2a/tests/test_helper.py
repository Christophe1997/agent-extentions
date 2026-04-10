#!/usr/bin/env python3
"""
Unit tests for a2a-helper.py — parser, auth, timeout, and session commands.

Run:
  python3 tests/test_helper.py
  python3 -m pytest tests/test_helper.py -v   # with pytest
"""
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

# Load helper as a module without triggering main()
_HELPER_PATH = Path(__file__).parent.parent / "scripts" / "a2a-helper.py"
_spec = importlib.util.spec_from_file_location("helper", _HELPER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load helper from {_HELPER_PATH}")
helper = importlib.util.module_from_spec(_spec)
sys.argv = ["a2a-helper.py"]
_spec.loader.exec_module(helper)  # type: ignore[union-attr]


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestParseFrontmatter(unittest.TestCase):

    def _parse(self, text):
        return helper._parse_frontmatter(text)

    def test_quoted_url_key_in_auth(self):
        text = """---
agents:
  echo: "http://localhost:9999"
auth:
  "http://localhost:9999":
    - "Authorization=Bearer test-token"
timeout: "10s"
---"""
        result = self._parse(text)
        self.assertEqual(result["agents"], {"echo": "http://localhost:9999"})
        self.assertIn("http://localhost:9999", result["auth"])
        self.assertEqual(result["auth"]["http://localhost:9999"], ["Authorization=Bearer test-token"])
        self.assertEqual(result["timeout"], "10s")

    def test_unquoted_url_key_in_auth(self):
        """Unquoted http(s):// keys must also parse correctly."""
        text = """---
agents:
  echo: "http://localhost:9999"
auth:
  http://localhost:9999:
    - "Authorization=Bearer test-token"
timeout: "10s"
---"""
        result = self._parse(text)
        self.assertEqual(result["agents"], {"echo": "http://localhost:9999"})
        self.assertIn("http://localhost:9999", result["auth"])
        self.assertEqual(result["timeout"], "10s")

    def test_https_url_with_path(self):
        text = """---
agents:
  prod: "https://api.example.com/a2a"
auth:
  "https://api.example.com":
    - "Authorization=Bearer abc"
    - "X-Tenant-ID=my-org"
---"""
        result = self._parse(text)
        self.assertEqual(result["agents"], {"prod": "https://api.example.com/a2a"})
        self.assertEqual(result["auth"]["https://api.example.com"],
                         ["Authorization=Bearer abc", "X-Tenant-ID=my-org"])

    def test_global_timeout(self):
        text = """---
timeout: "60s"
---"""
        self.assertEqual(self._parse(text)["timeout"], "60s")

    def test_per_url_timeouts(self):
        text = """---
timeouts:
  "https://slow.example.com": "120s"
---"""
        result = self._parse(text)
        self.assertEqual(result["timeouts"]["https://slow.example.com"], "120s")

    def test_no_frontmatter(self):
        self.assertEqual(self._parse("just text"), {})

    def test_empty_frontmatter(self):
        self.assertEqual(self._parse("---\n---"), {})

    def test_comments_ignored(self):
        text = """---
# this is a comment
agents:
  foo: "http://foo.example.com"
---"""
        self.assertEqual(self._parse(text)["agents"], {"foo": "http://foo.example.com"})


# ── Auth longest-prefix matching ──────────────────────────────────────────────

class TestAuthLongestPrefix(unittest.TestCase):

    def _auth(self, url, settings_text):
        return helper._resolve_auth(url, helper._parse_frontmatter(settings_text))

    def test_exact_prefix_match(self):
        text = """---
auth:
  "http://localhost:8000":
    - "Authorization=Bearer abcd"
---"""
        result = self._auth("http://localhost:8000/api/v1", text)
        self.assertEqual(result, ["Authorization=Bearer abcd"])

    def test_longest_prefix_wins(self):
        text = """---
auth:
  "https://api.example.com":
    - "Authorization=Bearer short"
  "https://api.example.com/v2":
    - "Authorization=Bearer long"
---"""
        result = self._auth("https://api.example.com/v2/resource", text)
        self.assertEqual(result, ["Authorization=Bearer long"])

    def test_no_match_returns_empty(self):
        text = """---
auth:
  "http://other.example.com":
    - "Authorization=Bearer nope"
---"""
        result = self._auth("http://localhost:9999", text)
        self.assertEqual(result, [])


# ── Timeout resolution ────────────────────────────────────────────────────────

class TestTimeoutCommand(unittest.TestCase):

    def _timeout(self, url, settings_text):
        return helper._resolve_timeout(url, helper._parse_frontmatter(settings_text))

    def test_global_timeout(self):
        text = "---\ntimeout: \"60s\"\n---"
        self.assertEqual(self._timeout("http://any.example.com", text), "60s")

    def test_per_url_overrides_global(self):
        text = """---
timeout: "30s"
timeouts:
  "http://slow.example.com": "120s"
---"""
        self.assertEqual(self._timeout("http://slow.example.com/api", text), "120s")
        self.assertEqual(self._timeout("http://other.example.com", text), "30s")

    def test_no_timeout_returns_empty(self):
        text = "---\nagents:\n  foo: \"http://foo\"\n---"
        self.assertEqual(self._timeout("http://foo", text), "")


# ── find-settings ────────────────────────────────────────────────────────────

class TestFindSettings(unittest.TestCase):
    """find-settings returns 'found:<path>' or 'missing:<preferred-path>'."""

    _HELPER = Path(__file__).parent.parent / "scripts" / "a2a-helper.py"

    def _run_cli(self, env=None):
        return self._run_cli_in(cwd=None, env=env)

    def _run_cli_in(self, cwd=None, env=None):
        result = subprocess.run(
            [sys.executable, str(self._HELPER), "find-settings"],
            capture_output=True, text=True, env=env, cwd=cwd,
        )
        return result.returncode, result.stdout.strip()

    def test_found_in_home(self):
        """Settings file at ~/.claude/a2a.local.md is reported as found."""
        import tempfile
        with tempfile.TemporaryDirectory() as home_dir:
            settings = Path(home_dir) / ".claude" / "a2a.local.md"
            settings.parent.mkdir(parents=True)
            settings.write_text("---\nagents: {}\n---\n")

            # Point HOME at the temp dir so Path.home() resolves there;
            # also set a non-existent CWD so home is the only match.
            env = os.environ.copy()
            env["HOME"] = home_dir
            env["PWD"] = home_dir  # cwd check uses Path.cwd() which reads PWD on some platforms

            rc, out = self._run_cli(env=env)
            self.assertEqual(rc, 0)
            self.assertTrue(out.startswith("found:"), f"Expected 'found:...', got: {out!r}")
            self.assertIn(".claude/a2a.local.md", out)

    def test_cwd_takes_priority_over_home(self):
        """CWD-local settings file takes priority over ~/.claude/a2a.local.md."""
        import tempfile
        with tempfile.TemporaryDirectory() as home_dir, \
             tempfile.TemporaryDirectory() as cwd_dir:
            for d in [home_dir, cwd_dir]:
                settings = Path(d) / ".claude" / "a2a.local.md"
                settings.parent.mkdir(parents=True)
                settings.write_text("---\nagents: {}\n---\n")

            env = os.environ.copy()
            env["HOME"] = home_dir

            rc, out = self._run_cli_in(cwd=cwd_dir, env=env)
            self.assertEqual(rc, 0)
            self.assertTrue(out.startswith("found:"), f"Expected 'found:...', got: {out!r}")
            self.assertIn(cwd_dir, out)
            self.assertNotIn(home_dir, out)

    def test_missing_returns_preferred_path(self):
        """When no settings file exists, output is 'missing:<home>/.claude/a2a.local.md'."""
        import tempfile
        with tempfile.TemporaryDirectory() as home_dir:
            env = os.environ.copy()
            env["HOME"] = home_dir

            rc, out = self._run_cli(env=env)
            self.assertEqual(rc, 0)
            self.assertTrue(out.startswith("missing:"), f"Expected 'missing:...', got: {out!r}")
            self.assertIn(home_dir, out)
            self.assertIn(".claude/a2a.local.md", out)

    def test_output_is_parseable_prefix_colon_path(self):
        """Output always follows '<status>:<path>' — no extra whitespace or newlines."""
        import tempfile
        with tempfile.TemporaryDirectory() as home_dir:
            env = os.environ.copy()
            env["HOME"] = home_dir
            _, out = self._run_cli(env=env)
            status, _, path = out.partition(":")
            self.assertIn(status, ("found", "missing"))
            self.assertTrue(path, "Path portion must not be empty")
            self.assertFalse(path.startswith(" "), "Path must not have leading space")


# ── Integration test: a2a serve --echo ────────────────────────────────────────

class TestAgainstEchoServer(unittest.TestCase):
    """Spin up `a2a serve --echo` and exercise the CLI commands used by skills."""

    PORT = 19999
    BASE_URL = f"http://localhost:{PORT}"

    @classmethod
    def setUpClass(cls):
        import time
        cls.proc = subprocess.Popen(
            ["a2a", "serve", "--echo", "--port", str(cls.PORT), "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.8)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait()

    def _run(self, *args):
        result = subprocess.run(["a2a"] + list(args), capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def test_discover(self):
        rc, out, _ = self._run("discover", self.BASE_URL)
        self.assertEqual(rc, 0)
        self.assertIn("Interfaces:", out)

    def test_send_blocking(self):
        rc, out, _ = self._run("send", self.BASE_URL, "hello echo")
        self.assertEqual(rc, 0)
        self.assertIn("hello echo", out)
        self.assertIn("completed", out)

    def test_send_and_get_task(self):
        _, out, _ = self._run("send", self.BASE_URL, "task status test")
        task_id = next(
            (line.split()[1] for line in out.splitlines() if line.startswith("Task:")),
            None,
        )
        self.assertIsNotNone(task_id, "No task ID found in send output")
        rc, out2, _ = self._run("get", "task", self.BASE_URL, task_id)
        self.assertEqual(rc, 0)
        self.assertIn(task_id, out2)
        self.assertIn("completed", out2)

    def test_cancel_completed_task_errors(self):
        """Canceling an already-completed task should fail with a clear error."""
        _, out, _ = self._run("send", self.BASE_URL, "cancel test")
        task_id = next(
            (line.split()[1] for line in out.splitlines() if line.startswith("Task:")),
            None,
        )
        rc, _, err = self._run("cancel", self.BASE_URL, task_id)
        self.assertNotEqual(rc, 0)
        self.assertIn("non-cancelable", err)

    def test_session_tracking(self):
        """session add + session list round-trip."""
        env = os.environ.copy()
        env["CLAUDE_SESSION_ID"] = "test-session-12345"

        task_id = "test-task-001"
        subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "a2a-helper.py"),
             "session", "add", task_id, self.BASE_URL,
             "--alias", "echo-test", "--message", "session round-trip"],
            env=env, capture_output=True,
        )
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "a2a-helper.py"),
             "session", "list"],
            env=env, capture_output=True, text=True,
        )
        self.assertIn(task_id, result.stdout)
        self.assertIn("echo-test", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
