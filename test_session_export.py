"""
Test suite for the Session Summary Export feature (Version 2).

Run with:  python -m unittest test_session_export -v
"""

import io
import os
import shutil
import unittest
from contextlib import redirect_stderr
from unittest import mock

from session_export import (
    API_KEY_ENV_VAR,
    fetch_board_data,
    get_api_key,
    main,
    format_summary,
    export_to_file,
    get_environment_config,
    ENVIRONMENTS,
)


class TestEnvironmentConfig(unittest.TestCase):

    def test_dev_environment_exists(self):
        config = get_environment_config("dev")
        self.assertEqual(config["label"], "Development")

    def test_test_environment_exists(self):
        config = get_environment_config("test")
        self.assertEqual(config["label"], "Test")

    def test_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            get_environment_config("production-typo")


class TestApiKeyHandling(unittest.TestCase):

    def test_env_var_is_used_when_set(self):
        with mock.patch.dict(os.environ, {API_KEY_ENV_VAR: "env-key"}):
            self.assertEqual(get_api_key("cli-key"), "env-key")

    def test_cli_value_used_when_env_var_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_api_key("cli-key"), "cli-key")

    def test_no_key_returns_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_api_key())


class TestFetchBoardData(unittest.TestCase):

    def test_mock_data_returned_without_api_key(self):
        data = fetch_board_data("BOARD-001", env_name="test")
        self.assertEqual(data["board_id"], "BOARD-001")
        self.assertIn("comments", data)
        self.assertIn("tasks", data)

    def test_blank_board_id_raises(self):
        with self.assertRaises(ValueError):
            fetch_board_data("   ", env_name="test")

    def test_live_api_call_not_implemented_yet(self):
        with self.assertRaises(NotImplementedError):
            fetch_board_data("BOARD-001", env_name="test", api_key="fake-key")


class TestFormatSummary(unittest.TestCase):

    def setUp(self):
        self.data = fetch_board_data("BOARD-001", env_name="test")

    def test_summary_includes_board_title(self):
        summary = format_summary(self.data, env_name="test")
        self.assertIn(self.data["board_title"], summary)

    def test_summary_includes_environment_label(self):
        summary = format_summary(self.data, env_name="test")
        self.assertIn("**Environment:** Test", summary)

    def test_summary_shows_development_label_for_dev(self):
        summary = format_summary(self.data, env_name="dev")
        self.assertIn("**Environment:** Development", summary)

    def test_summary_lists_all_comments(self):
        summary = format_summary(self.data, env_name="test")
        for comment in self.data["comments"]:
            self.assertIn(comment["author"], summary)

    def test_summary_lists_all_tasks(self):
        summary = format_summary(self.data, env_name="test")
        for task in self.data["tasks"]:
            self.assertIn(task["title"], summary)

    def test_summary_handles_empty_board(self):
        empty_data = {
            "board_id": "EMPTY-001",
            "board_title": "Empty Board",
            "comments": [],
            "tasks": [],
        }
        summary = format_summary(empty_data, env_name="test")
        self.assertIn("No comments found", summary)
        self.assertIn("No tasks found", summary)

    def test_totals_count_open_items_correctly(self):
        summary = format_summary(self.data, env_name="test")
        expected_open_comments = sum(1 for c in self.data["comments"] if not c["resolved"])
        self.assertIn(f"{expected_open_comments} open", summary)

    def test_totals_count_incomplete_tasks_correctly(self):
        summary = format_summary(self.data, env_name="test")
        expected_open_tasks = sum(1 for t in self.data["tasks"] if t["status"] != "Complete")
        self.assertIn(f"{expected_open_tasks} not complete", summary)


class TestExportToFile(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_output_tmp"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_is_written(self):
        path = os.path.join(self.test_dir, "summary.md")
        export_to_file("# Test content", path)
        self.assertTrue(os.path.exists(path))

    def test_file_content_matches(self):
        path = os.path.join(self.test_dir, "summary.md")
        export_to_file("# Test content", path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "# Test content")


class TestEndToEndTestStagePromotion(unittest.TestCase):
    """
    Full pipeline test simulating the Version 2 to Test promotion:
    fetch -> format -> export, run against the Test environment.
    """

    def setUp(self):
        self.test_dir = "test_output_tmp"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_pipeline_against_test_environment(self):
        data = fetch_board_data("BOARD-001", env_name="test")
        summary = format_summary(data, env_name="test")
        path = export_to_file(summary, os.path.join(self.test_dir, "session_summary.md"))

        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Session Summary Export", content)
        self.assertIn("Environment:** Test", content)


class TestMainErrorHandling(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_output_tmp"
        os.makedirs(self.test_dir, exist_ok=True)
        self.out = os.path.join(self.test_dir, "summary.md")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_main_succeeds_without_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code = main(["--env", "test", "--output", self.out])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(self.out))

    def test_main_reports_missing_live_integration_cleanly(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {API_KEY_ENV_VAR: "fake-key"}), redirect_stderr(err):
            code = main(["--env", "test", "--output", self.out])
        self.assertEqual(code, 2)
        self.assertIn("pending credential setup", err.getvalue())
        self.assertFalse(os.path.exists(self.out))

    def test_main_reports_blank_board_id(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stderr(err):
            code = main(["--board-id", " ", "--output", self.out])
        self.assertEqual(code, 1)
        self.assertIn("board ID is required", err.getvalue())


if __name__ == "__main__":
    unittest.main()
