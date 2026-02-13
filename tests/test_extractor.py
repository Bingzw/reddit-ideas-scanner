from __future__ import annotations

from pathlib import Path
import unittest

from reddit_ideas.config import AppConfig
from reddit_ideas.extractor import extract_ideas, score_post
from reddit_ideas.models import RedditPost


def make_config(min_score: float = 2.0) -> AppConfig:
    return AppConfig(
        subreddits=["vibecoding", "AppIdeas", "freelance", "passive_income"],
        lookback_hours=168,
        max_posts_per_subreddit=20,
        min_score=min_score,
        report_top_n=10,
        data_dir=Path("data"),
        output_dir=Path("output"),
        user_agent="test-agent",
        include_keywords=["problem", "manual", "automate", "tool", "app", "passive income"],
        exclude_keywords=["hiring"],
        smtp=None,
        telegram=None,
    )


class ExtractorTests(unittest.TestCase):
    def test_score_relevant_post_is_high(self) -> None:
        post = RedditPost(
            post_id="abc123",
            subreddit="AppIdeas",
            title="What manual workflow problem should I automate for passive income?",
            selftext="I want to build an app tool because manual reporting is frustrating for teams.",
            permalink="https://reddit.com/r/AppIdeas/abc123",
            url="https://reddit.com/r/AppIdeas/abc123",
            author="user1",
            created_utc=1_700_000_000,
            num_comments=24,
            upvotes=120,
            is_self=True,
        )
        score, tags = score_post(post, make_config())

        self.assertGreater(score, 3.5)
        self.assertIn("keyword_match", tags)
        self.assertIn("pain_point", tags)
        self.assertIn("solution_possible", tags)

    def test_extract_filters_low_signal_posts(self) -> None:
        posts = [
            RedditPost(
                post_id="good1",
                subreddit="vibecoding",
                title="Automation idea: build a tool to reduce repetitive QA",
                selftext="Current process is manual and slow. Could this become a SaaS?",
                permalink="https://reddit.com/r/vibecoding/good1",
                url="https://reddit.com/r/vibecoding/good1",
                author="user2",
                created_utc=1_700_000_100,
                num_comments=8,
                upvotes=30,
                is_self=True,
            ),
            RedditPost(
                post_id="bad1",
                subreddit="freelance",
                title="Weekend photos from my trip",
                selftext="No work ideas here.",
                permalink="https://reddit.com/r/freelance/bad1",
                url="https://reddit.com/r/freelance/bad1",
                author="user3",
                created_utc=1_700_000_200,
                num_comments=0,
                upvotes=1,
                is_self=True,
            ),
        ]
        ideas = extract_ideas(posts, make_config(min_score=2.0))

        self.assertEqual(len(ideas), 1)
        self.assertEqual(ideas[0].post_id, "good1")


if __name__ == "__main__":
    unittest.main()
