from __future__ import annotations

from pathlib import Path
import unittest

from reddit_ideas.config import AppConfig, GeminiConfig
from reddit_ideas.llm_assessor import GeminiAssessment, enrich_ideas_with_gemini
from reddit_ideas.models import IdeaCandidate, RedditPost


class FakeGeminiAssessor:
    def __init__(self) -> None:
        self.calls = 0

    def assess(self, post: RedditPost, idea: IdeaCandidate) -> GeminiAssessment | None:
        self.calls += 1
        return GeminiAssessment(
            profit_score=82.0,
            confidence=0.74,
            summary=f"LLM summary for {post.title}"[:240],
            monetization_hint="Charge for automation as a monthly SaaS.",
            reason_tags=["llm_real_pain", "llm_pays_signal"],
        )


def build_config() -> AppConfig:
    return AppConfig(
        subreddits=["vibecoding"],
        lookback_hours=168,
        max_posts_per_subreddit=10,
        min_score=2.0,
        report_top_n=10,
        data_dir=Path("data"),
        output_dir=Path("output"),
        user_agent="test-agent",
        include_keywords=["problem", "manual", "automate", "tool", "app", "passive income"],
        exclude_keywords=["hiring"],
        smtp=None,
        telegram=None,
        gemini=GeminiConfig(
            enabled=True,
            api_key="fake-key",
            model="gemini-2.5-flash-lite",
            temperature=0.2,
            max_candidates=2,
            timeout_seconds=20,
        ),
    )


class LlmAssessorTests(unittest.TestCase):
    def test_enrichment_updates_top_candidates(self) -> None:
        posts = [
            RedditPost(
                post_id="1",
                subreddit="vibecoding",
                title="Automate reporting for ops teams",
                selftext="Manual reporting is slow and painful.",
                permalink="https://reddit.com/r/vibecoding/1",
                url="https://reddit.com/r/vibecoding/1",
                author="u1",
                created_utc=1_700_000_000,
                num_comments=3,
                upvotes=20,
                is_self=True,
            ),
            RedditPost(
                post_id="2",
                subreddit="vibecoding",
                title="Low signal item",
                selftext="Some post text.",
                permalink="https://reddit.com/r/vibecoding/2",
                url="https://reddit.com/r/vibecoding/2",
                author="u2",
                created_utc=1_700_000_010,
                num_comments=1,
                upvotes=2,
                is_self=True,
            ),
            RedditPost(
                post_id="3",
                subreddit="vibecoding",
                title="Third item not assessed due to max_candidates",
                selftext="Manual work problem for a niche.",
                permalink="https://reddit.com/r/vibecoding/3",
                url="https://reddit.com/r/vibecoding/3",
                author="u3",
                created_utc=1_700_000_020,
                num_comments=0,
                upvotes=1,
                is_self=True,
            ),
        ]
        ideas = [
            IdeaCandidate(
                post_id="1",
                subreddit="vibecoding",
                title="Automate reporting for ops teams",
                problem_summary="old summary",
                solution_hint="old hint",
                relevance_score=4.0,
                reason_tags=["pain_point"],
                created_utc=1_700_000_000,
                permalink="https://reddit.com/r/vibecoding/1",
                url="https://reddit.com/r/vibecoding/1",
                author="u1",
                num_comments=3,
                upvotes=20,
            ),
            IdeaCandidate(
                post_id="2",
                subreddit="vibecoding",
                title="Low signal item",
                problem_summary="old summary",
                solution_hint="old hint",
                relevance_score=3.8,
                reason_tags=["pain_point"],
                created_utc=1_700_000_010,
                permalink="https://reddit.com/r/vibecoding/2",
                url="https://reddit.com/r/vibecoding/2",
                author="u2",
                num_comments=1,
                upvotes=2,
            ),
            IdeaCandidate(
                post_id="3",
                subreddit="vibecoding",
                title="Third item",
                problem_summary="old summary",
                solution_hint="old hint",
                relevance_score=1.1,
                reason_tags=["pain_point"],
                created_utc=1_700_000_020,
                permalink="https://reddit.com/r/vibecoding/3",
                url="https://reddit.com/r/vibecoding/3",
                author="u3",
                num_comments=0,
                upvotes=1,
            ),
        ]

        fake = FakeGeminiAssessor()
        enriched = enrich_ideas_with_gemini(
            ideas=ideas,
            posts=posts,
            config=build_config(),
            assessor=fake,
        )

        self.assertEqual(fake.calls, 2)
        top = next(item for item in enriched if item.post_id == "1")
        untouched = next(item for item in enriched if item.post_id == "3")

        self.assertIsNotNone(top.llm_profit_score)
        self.assertIn("llm_assessed", top.reason_tags)
        self.assertIn("llm_real_pain", top.reason_tags)
        self.assertTrue(top.problem_summary.startswith("LLM summary"))
        self.assertGreater(top.relevance_score, 4.0)

        self.assertIsNone(untouched.llm_profit_score)
        self.assertNotIn("llm_assessed", untouched.reason_tags)


if __name__ == "__main__":
    unittest.main()
