"""Reddit ingestion using public JSON endpoints (no OAuth required).

Uses three endpoint templates in order; if one returns an error the next is
tried automatically.  Pagination is handled via Reddit's ``after`` cursor so
up to ``max_posts`` posts can be collected per subreddit per run.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .models import RedditPost

# Tried in order; old.reddit.com is a fallback that sometimes bypasses 403s
REDDIT_NEW_ENDPOINTS = (
    "https://www.reddit.com/r/{sub}/new.json",
    "https://api.reddit.com/r/{sub}/new",
    "https://old.reddit.com/r/{sub}/new.json",
)


class RedditClient:
    def __init__(self, user_agent: str, timeout_seconds: int = 20, max_retries: int = 3) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def fetch_new_posts(self, subreddit: str, limit: int) -> list[RedditPost]:
        return self.fetch_new_posts_since(subreddit=subreddit, since_utc=0, max_posts=limit)

    def fetch_new_posts_since(
        self, subreddit: str, since_utc: int, max_posts: int
    ) -> list[RedditPost]:
        endpoint_errors: list[str] = []
        encoded_subreddit = urllib.parse.quote(subreddit)
        for endpoint_template in REDDIT_NEW_ENDPOINTS:
            endpoint = endpoint_template.format(sub=encoded_subreddit)
            try:
                return self._fetch_from_endpoint(endpoint, subreddit, since_utc, max_posts)
            except RuntimeError as exc:
                endpoint_errors.append(str(exc))

        summary = " | ".join(endpoint_errors[-3:])
        raise RuntimeError(f"All Reddit endpoints failed for r/{subreddit}: {summary}")

    def _fetch_from_endpoint(
        self, endpoint: str, subreddit: str, since_utc: int, max_posts: int
    ) -> list[RedditPost]:
        normalized_max = max(max_posts, 1)
        posts: list[RedditPost] = []
        after: str | None = None
        stop = False

        while len(posts) < normalized_max and not stop:
            query_params: dict[str, int | str] = {
                "limit": min(normalized_max - len(posts), 100),  # Reddit max per page is 100
                "raw_json": 1,
            }
            if after:
                query_params["after"] = after  # Pagination cursor from previous page
            query = urllib.parse.urlencode(query_params)
            url = f"{endpoint}?{query}"

            payload = self._get_json(url)
            children = payload.get("data", {}).get("children", [])
            if not children:
                break

            for child in children:
                post = self._parse_post(child=child, fallback_subreddit=subreddit)
                if post is None:
                    continue
                if post.created_utc < since_utc:
                    # Posts are sorted newest-first; once we pass the floor we can stop
                    stop = True
                    break
                posts.append(post)
                if len(posts) >= normalized_max:
                    break

            after = payload.get("data", {}).get("after")
            if not after:
                break

        return posts

    def _parse_post(self, child: dict, fallback_subreddit: str) -> RedditPost | None:
        data = child.get("data", {})
        post_id = data.get("id")
        if not post_id:
            return None
        return RedditPost(
            post_id=post_id,
            subreddit=data.get("subreddit", fallback_subreddit),
            title=data.get("title", "").strip(),
            selftext=data.get("selftext", "").strip(),
            permalink="https://reddit.com" + data.get("permalink", ""),
            url=data.get("url", ""),
            author=data.get("author", "[deleted]"),
            created_utc=int(data.get("created_utc", 0)),
            num_comments=int(data.get("num_comments", 0)),
            upvotes=int(data.get("ups", 0)),
            is_self=bool(data.get("is_self", False)),
        )

    def _get_json(self, url: str) -> dict:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            request = urllib.request.Request(
                url=url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw)
            except urllib.error.HTTPError as exc:
                hint = ""
                if exc.code == 403:
                    hint = (
                        " (blocked by endpoint; try a more specific User-Agent like "
                        "'windows:reddit_ideas_scanner:1.0 (by /u/<yourname>)')"
                    )
                last_error = RuntimeError(f"HTTP {exc.code} for {url}{hint}")
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
        if last_error is None:
            raise RuntimeError("Failed to fetch URL: unknown error")
        raise RuntimeError(f"Failed to fetch URL: {url}. Cause: {last_error}") from last_error
