from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
import unittest

from reddit_ideas.config import AppConfig
from reddit_ideas.models import RedditPost
from reddit_ideas.pipeline import run_once


class FakeRedditClient:
    def __init__(self, posts_by_subreddit: dict[str, list[RedditPost]]) -> None:
        self.posts_by_subreddit = posts_by_subreddit
        self.calls: list[tuple[str, int, int]] = []

    def fetch_new_posts(self, subreddit: str, limit: int) -> list[RedditPost]:
        posts = self.posts_by_subreddit.get(subreddit, [])
        return posts[:limit]

    def fetch_new_posts_since(
        self, subreddit: str, since_utc: int, max_posts: int
    ) -> list[RedditPost]:
        self.calls.append((subreddit, since_utc, max_posts))
        posts = self.posts_by_subreddit.get(subreddit, [])
        filtered = [post for post in posts if post.created_utc >= since_utc]
        return filtered[:max_posts]


class FakeNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Path]] = []

    def send(self, subject: str, body: str, report_path: Path) -> None:
        self.calls.append((subject, body, report_path))


def build_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        subreddits=["vibecoding", "AppIdeas", "freelance", "passive_income"],
        lookback_hours=168,
        max_posts_per_subreddit=10,
        min_score=2.0,
        report_top_n=10,
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        user_agent="test-agent",
        include_keywords=["problem", "manual", "automate", "tool", "app", "passive income"],
        exclude_keywords=["hiring"],
        smtp=None,
        telegram=None,
    )


class PipelineTests(unittest.TestCase):
    def test_run_once_generates_csv_and_report(self) -> None:
        now = datetime(2026, 2, 12, 12, 0, tzinfo=UTC)
        recent_utc = int(now.timestamp()) - 3600

        posts = {
            "vibecoding": [
                RedditPost(
                    post_id="x1",
                    subreddit="vibecoding",
                    title="Tool idea to automate bug triage workflow",
                    selftext="This manual process is frustrating and slow.",
                    permalink="https://reddit.com/r/vibecoding/x1",
                    url="https://reddit.com/r/vibecoding/x1",
                    author="u1",
                    created_utc=recent_utc,
                    num_comments=12,
                    upvotes=40,
                    is_self=True,
                )
            ],
            "AppIdeas": [],
            "freelance": [],
            "passive_income": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = build_config(tmp_path)
            fake_client = FakeRedditClient(posts)
            fake_notifier = FakeNotifier()

            result = run_once(
                config=config,
                period="daily",
                reddit_client=fake_client,
                notifier=fake_notifier,
                now=now,
            )

            self.assertEqual(result.status, "success")
            self.assertEqual(result.fetched_posts, 1)
            self.assertGreaterEqual(result.extracted_ideas, 1)
            self.assertIsNotNone(result.csv_path)
            self.assertIsNotNone(result.report_path)
            self.assertTrue(result.csv_path.exists())
            self.assertTrue(result.report_path.exists())
            self.assertEqual(len(fake_notifier.calls), 1)

    def test_duplicate_run_same_day_is_skipped(self) -> None:
        now = datetime(2026, 2, 12, 12, 0, tzinfo=UTC)
        recent_utc = int(now.timestamp()) - 3600
        posts = {
            "vibecoding": [
                RedditPost(
                    post_id="x1",
                    subreddit="vibecoding",
                    title="Tool idea to automate bug triage workflow",
                    selftext="This manual process is frustrating and slow.",
                    permalink="https://reddit.com/r/vibecoding/x1",
                    url="https://reddit.com/r/vibecoding/x1",
                    author="u1",
                    created_utc=recent_utc,
                    num_comments=12,
                    upvotes=40,
                    is_self=True,
                )
            ],
            "AppIdeas": [],
            "freelance": [],
            "passive_income": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = build_config(tmp_path)
            fake_client = FakeRedditClient(posts)
            fake_notifier = FakeNotifier()

            first = run_once(
                config=config,
                period="daily",
                reddit_client=fake_client,
                notifier=fake_notifier,
                now=now,
            )
            second = run_once(
                config=config,
                period="daily",
                reddit_client=fake_client,
                notifier=fake_notifier,
                now=now,
            )

            self.assertEqual(first.status, "success")
            self.assertEqual(second.status, "skipped_same_day")
            self.assertEqual(second.fetched_posts, 0)
            self.assertEqual(second.extracted_ideas, 0)
            self.assertIsNone(second.csv_path)
            self.assertIsNone(second.report_path)
            self.assertEqual(len(fake_notifier.calls), 1)

    def test_second_run_within_7_days_uses_last_success_time(self) -> None:
        first_run_time = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
        second_run_time = datetime(2026, 2, 2, 12, 0, tzinfo=UTC)
        post_time = int(second_run_time.timestamp()) - 1800
        old_post_time = int(first_run_time.timestamp()) - (8 * 24 * 60 * 60)

        posts = {
            "vibecoding": [
                RedditPost(
                    post_id="new_post",
                    subreddit="vibecoding",
                    title="Automate weekly status updates",
                    selftext="Manual updates are slow and repetitive.",
                    permalink="https://reddit.com/r/vibecoding/new_post",
                    url="https://reddit.com/r/vibecoding/new_post",
                    author="u1",
                    created_utc=post_time,
                    num_comments=8,
                    upvotes=32,
                    is_self=True,
                ),
                RedditPost(
                    post_id="old_post",
                    subreddit="vibecoding",
                    title="Old post outside incremental window",
                    selftext="An older post that should not be refetched after first run.",
                    permalink="https://reddit.com/r/vibecoding/old_post",
                    url="https://reddit.com/r/vibecoding/old_post",
                    author="u2",
                    created_utc=old_post_time,
                    num_comments=1,
                    upvotes=2,
                    is_self=True,
                ),
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = build_config(tmp_path)
            config.subreddits = ["vibecoding"]
            fake_client = FakeRedditClient(posts)

            run_once(
                config=config,
                period="daily",
                reddit_client=fake_client,
                notifier=None,
                now=first_run_time,
            )
            run_once(
                config=config,
                period="daily",
                reddit_client=fake_client,
                notifier=None,
                now=second_run_time,
            )

            self.assertGreaterEqual(len(fake_client.calls), 2)
            first_since = fake_client.calls[0][1]
            second_since = fake_client.calls[1][1]
            expected_first_floor = int(first_run_time.timestamp()) - (7 * 24 * 60 * 60)
            self.assertEqual(first_since, expected_first_floor)
            self.assertEqual(second_since, int(first_run_time.timestamp()))


if __name__ == "__main__":
    unittest.main()
