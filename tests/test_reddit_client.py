from __future__ import annotations

import unittest
import urllib.error
from unittest.mock import patch

from reddit_ideas.reddit_client import RedditClient


class FallbackClient(RedditClient):
    def __init__(self) -> None:
        super().__init__(user_agent="test-agent", timeout_seconds=1, max_retries=1)
        self.urls: list[str] = []

    def _get_json(self, url: str) -> dict:
        self.urls.append(url)
        if "www.reddit.com" in url:
            raise RuntimeError(f"Failed to fetch URL: {url}")
        return {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "subreddit": "vibecoding",
                            "title": "Post title",
                            "selftext": "Post body",
                            "permalink": "/r/vibecoding/comments/abc123/post_title/",
                            "url": "https://reddit.com/r/vibecoding/comments/abc123/post_title/",
                            "author": "user1",
                            "created_utc": 1_700_000_000,
                            "num_comments": 3,
                            "ups": 9,
                            "is_self": True,
                        }
                    }
                ],
                "after": None,
            }
        }


class RedditClientTests(unittest.TestCase):
    def test_fetch_uses_fallback_endpoint_when_first_is_blocked(self) -> None:
        client = FallbackClient()
        posts = client.fetch_new_posts_since("vibecoding", since_utc=0, max_posts=10)

        self.assertEqual(len(posts), 1)
        self.assertGreaterEqual(len(client.urls), 2)
        self.assertIn("www.reddit.com", client.urls[0])
        self.assertIn("api.reddit.com", client.urls[1])

    def test_403_message_includes_user_agent_hint(self) -> None:
        client = RedditClient(user_agent="test-agent", timeout_seconds=1, max_retries=1)
        http_403 = urllib.error.HTTPError(
            url="https://www.reddit.com/r/vibecoding/new.json?limit=1",
            code=403,
            msg="Blocked",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_403):
            with self.assertRaises(RuntimeError) as ctx:
                client._get_json("https://www.reddit.com/r/vibecoding/new.json?limit=1")

        message = str(ctx.exception).lower()
        self.assertIn("failed to fetch url", message)
        self.assertIn("403", message)
        self.assertIn("user-agent", message)


if __name__ == "__main__":
    unittest.main()
