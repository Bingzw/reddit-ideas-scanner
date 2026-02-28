from __future__ import annotations

import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from reddit_ideas.cli import main
from reddit_ideas.config import AppConfig, SmtpConfig


def build_config(base_dir: Path, smtp: SmtpConfig | None) -> AppConfig:
    return AppConfig(
        subreddits=["vibecoding", "AppIdeas", "freelance", "passive_income"],
        lookback_hours=168,
        max_posts_per_subreddit=10,
        min_score=2.0,
        report_top_n=10,
        data_dir=base_dir / "data",
        output_dir=base_dir / "output",
        user_agent="test-agent",
        include_keywords=["problem", "manual", "automate", "tool", "app", "passive income"],
        exclude_keywords=["hiring"],
        smtp=smtp,
        telegram=None,
        gemini=None,
    )


class CliTests(unittest.TestCase):
    def test_run_once_passes_force_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = build_config(Path(tmpdir), smtp=None)
            with patch("reddit_ideas.cli.load_config", return_value=config):
                with patch("reddit_ideas.cli.run_once") as run_once_mock:
                    run_once_mock.return_value = type(
                        "Result",
                        (),
                        {
                            "status": "success",
                            "fetched_posts": 0,
                            "extracted_ideas": 0,
                            "window_ideas": 0,
                            "email_sent": False,
                            "message": "ok",
                            "csv_path": None,
                            "report_path": None,
                        },
                    )()
                    rc = main(["run-once", "--period", "daily", "--force"])

            self.assertEqual(rc, 0)
            self.assertTrue(run_once_mock.called)
            kwargs = run_once_mock.call_args.kwargs
            self.assertEqual(kwargs["period"], "daily")
            self.assertTrue(kwargs["force"])

    def test_test_email_requires_smtp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = build_config(Path(tmpdir), smtp=None)
            with patch("reddit_ideas.cli.load_config", return_value=config):
                stdout = io.StringIO()
                with patch("sys.stdout", new=stdout):
                    rc = main(["test-email"])

            self.assertEqual(rc, 2)
            self.assertIn("SMTP is not configured", stdout.getvalue())

    def test_test_email_uses_email_notifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            smtp = SmtpConfig(
                host="smtp.example.com",
                port=587,
                user="sender@example.com",
                password="secret",
                email_to="receiver@example.com",
            )
            config = build_config(Path(tmpdir), smtp=smtp)

            with patch("reddit_ideas.cli.load_config", return_value=config):
                with patch("reddit_ideas.cli.EmailNotifier.send") as send_mock:
                    stdout = io.StringIO()
                    with patch("sys.stdout", new=stdout):
                        rc = main(["test-email", "--subject", "Probe"])

            self.assertEqual(rc, 0)
            send_mock.assert_called_once()
            self.assertIn("Test email sent successfully", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
