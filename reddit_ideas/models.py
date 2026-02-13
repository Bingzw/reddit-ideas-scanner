from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RedditPost:
    post_id: str
    subreddit: str
    title: str
    selftext: str
    permalink: str
    url: str
    author: str
    created_utc: int
    num_comments: int
    upvotes: int
    is_self: bool


@dataclass(slots=True)
class IdeaCandidate:
    post_id: str
    subreddit: str
    title: str
    problem_summary: str
    solution_hint: str
    relevance_score: float
    reason_tags: list[str]
    created_utc: int
    permalink: str
    url: str
    author: str
    num_comments: int
    upvotes: int
    llm_profit_score: float | None = None
    llm_confidence: float | None = None
