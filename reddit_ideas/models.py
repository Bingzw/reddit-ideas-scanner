from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RedditPost:
    """Normalized Reddit submission fields used by the pipeline.

    Attributes:
        post_id: Reddit post identifier (base36 id).
        subreddit: Subreddit name without the ``r/`` prefix.
        title: Post title text.
        selftext: Post body text for self posts, empty for link posts.
        permalink: Relative Reddit permalink path.
        url: Canonical outbound or Reddit URL for the post.
        author: Username string as returned by Reddit.
        created_utc: Post creation time as UTC epoch seconds.
        num_comments: Current comment count.
        upvotes: Current upvote score.
        is_self: True when the post is a text/self post.
    """

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
    """Scored idea candidate derived from a Reddit post.

    Attributes:
        post_id: Source Reddit post identifier.
        subreddit: Source subreddit name without the ``r/`` prefix.
        title: Source post title.
        problem_summary: Short statement of the user pain/problem.
        solution_hint: Suggested product direction.
        relevance_score: Final ranking score used in reports.
        reason_tags: Heuristic/LLM tags explaining the score.
        created_utc: Source post creation time as UTC epoch seconds.
        permalink: Relative Reddit permalink path.
        url: Canonical outbound or Reddit URL.
        author: Reddit username for the source post.
        num_comments: Source post comment count.
        upvotes: Source post upvote score.
        llm_profit_score: Optional profitability score from Gemini (0-100).
        llm_confidence: Optional confidence score from Gemini (0-1).
    """

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
