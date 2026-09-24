"""
Test suite for the Session Summary Export feature.

Run with:  python -m unittest test_session_export.py -v
"""

import os
import shutil
import unittest

from session_export import (
    fetch_board_data,
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


class TestFetchBoardData(unittest.TestCase):

    def test_mock_data_returned_without_api_key(self):
        data = fetch_board_data("BOARD-001", env_name="test")
        self.assertEqual(data["board_id"], "BOARD-001")
        self.assertIn("comments", data)
        self.assertIn("tasks", data)

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
        self.assertIn("Test", summary)

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
    Full pipeline test simulating the Version 1 to Test promotion:
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


if __name__ == "__main__":
    unittest.main()
