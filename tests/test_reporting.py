from __future__ import annotations

from datetime import UTC, datetime
import unittest

from reddit_ideas.models import IdeaCandidate
from reddit_ideas.reporting import build_markdown_report


class ReportingTests(unittest.TestCase):
    def test_build_markdown_report_contains_expected_sections(self) -> None:
        ideas = [
            IdeaCandidate(
                post_id="1",
                subreddit="AppIdeas",
                title="Invoice reminder app for freelancers",
                problem_summary="Freelancers forget to follow up on unpaid invoices.",
                solution_hint="Build reminders with payment status automation.",
                relevance_score=4.2,
                reason_tags=["keyword_match", "pain_point", "solution_possible"],
                created_utc=1_700_000_000,
                permalink="https://reddit.com/r/AppIdeas/1",
                url="https://reddit.com/r/AppIdeas/1",
                author="u1",
                num_comments=10,
                upvotes=50,
            ),
            IdeaCandidate(
                post_id="2",
                subreddit="passive_income",
                title="Template marketplace for recurring revenue",
                problem_summary="People want ready-made systems to launch quickly.",
                solution_hint="Sell templates with monthly updates.",
                relevance_score=3.7,
                reason_tags=["keyword_match", "monetization"],
                created_utc=1_700_000_100,
                permalink="https://reddit.com/r/passive_income/2",
                url="https://reddit.com/r/passive_income/2",
                author="u2",
                num_comments=3,
                upvotes=20,
            ),
        ]
        report = build_markdown_report(
            ideas=ideas,
            period="daily",
            generated_at=datetime(2026, 2, 12, 10, 30, tzinfo=UTC),
            top_n=10,
        )

        self.assertIn("# Reddit Idea Scanner Report (Daily)", report)
        self.assertIn("## Top Opportunities", report)
        self.assertIn("## Subreddit Distribution", report)
        self.assertIn("r/AppIdeas: 1", report)
        self.assertIn("monetization: 1", report)


if __name__ == "__main__":
    unittest.main()
