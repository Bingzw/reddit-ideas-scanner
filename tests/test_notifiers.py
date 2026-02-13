from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from reddit_ideas.notifiers import EmailNotifier


class NotifierTests(unittest.TestCase):
    @patch("smtplib.SMTP")
    def test_email_notifier_sends_message(self, smtp_mock) -> None:
        notifier = EmailNotifier(
            host="smtp.example.com",
            port=587,
            user="sender@example.com",
            password="secret",
            email_to="receiver@example.com",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report = Path(tmpdir) / "report.md"
            report.write_text("# Test report\n", encoding="utf-8")

            notifier.send(
                subject="Reddit Ideas Daily Report",
                body="Captured 5 ideas.",
                report_path=report,
            )

        smtp_instance = smtp_mock.return_value.__enter__.return_value
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("sender@example.com", "secret")
        smtp_instance.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
