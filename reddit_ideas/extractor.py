"""Heuristic scoring and idea extraction from raw Reddit posts.

Each post is scored against keyword lists, pain/solution/monetization signals,
and engagement metrics. Posts that exceed ``config.min_score`` become
``IdeaCandidate`` objects ready for optional LLM enrichment.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .config import AppConfig
from .models import IdeaCandidate, RedditPost

WORD_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_+-]*")

# Substring patterns that indicate a user is describing a real problem
PAIN_SIGNALS = ["problem", "issue", "frustrat", "pain", "manual", "slow", "time-consuming", "stuck"]
# Patterns suggesting someone is looking for or building a solution
SOLUTION_SIGNALS = ["automate", "tool", "app", "website", "script", "plugin", "bot", "saas"]
# Patterns that indicate direct monetization interest
MONETIZATION_SIGNALS = ["passive income", "subscription", "monetiz", "affiliate", "mrr", "side hustle"]


def extract_ideas(posts: list[RedditPost], config: AppConfig) -> list[IdeaCandidate]:
    """Convert posts into sorted idea candidates above the score threshold.

    Args:
        posts: Raw Reddit posts fetched from configured subreddits.
        config: Application config containing scoring thresholds and keywords.

    Returns:
        List of ``IdeaCandidate`` objects sorted by descending relevance score.
    """

    ideas: list[IdeaCandidate] = []
    for post in posts:
        score, tags = score_post(post, config)
        if score < config.min_score:
            continue
        ideas.append(
            IdeaCandidate(
                post_id=post.post_id,
                subreddit=post.subreddit,
                title=post.title,
                problem_summary=derive_problem_summary(post),
                solution_hint=derive_solution_hint(post, tags),
                relevance_score=round(score, 3),
                reason_tags=tags,
                created_utc=post.created_utc,
                permalink=post.permalink,
                url=post.url,
                author=post.author,
                num_comments=post.num_comments,
                upvotes=post.upvotes,
            )
        )
    ideas.sort(key=lambda idea: idea.relevance_score, reverse=True)
    return ideas


def score_post(post: RedditPost, config: AppConfig) -> tuple[float, list[str]]:
    """Compute heuristic relevance score and reason tags for one post.

    Args:
        post: One Reddit post to evaluate.
        config: Application config with include/exclude keyword lists.

    Returns:
        Tuple ``(score, tags)`` where ``score`` is a float and ``tags`` is a
        list of short strings describing why the post was scored that way.
    """

    text = f"{post.title}\n{post.selftext}".lower()
    tags: list[str] = []
    score = 0.0

    # Keyword relevance: +0.45 per hit, capped at 3.0 to avoid keyword-stuffed posts
    include_hits = _keyword_hits(text, config.include_keywords)
    if include_hits:
        score += min(include_hits * 0.45, 3.0)
        tags.append("keyword_match")

    # Noise penalty: -0.9 per hit, capped at 2.5
    exclude_hits = _keyword_hits(text, config.exclude_keywords)
    if exclude_hits:
        score -= min(exclude_hits * 0.9, 2.5)
        tags.append("noise_signal")

    if _contains_any(text, PAIN_SIGNALS):
        score += 0.9
        tags.append("pain_point")
    if _contains_any(text, SOLUTION_SIGNALS):
        score += 0.9
        tags.append("solution_possible")
    if _contains_any(text, MONETIZATION_SIGNALS):
        score += 1.1  # Weighted higher: explicit monetization intent is a strong signal
        tags.append("monetization")

    # Engagement signals: log-scaled so viral posts don't dominate
    score += min(math.log10(max(post.num_comments, 1)), 1.0) * 0.5
    score += min(math.log10(max(post.upvotes, 1)), 2.0) * 0.35

    title_tokens = _tokenize(post.title)
    if len(title_tokens) >= 6:
        score += 0.2  # Longer titles tend to be more descriptive and specific
    if "?" in post.title:
        score += 0.25  # Questions often indicate genuine community discussion
        tags.append("question")

    if "discussion" in text or "idea" in text or "feedback" in text:
        score += 0.15

    if not tags:
        tags.append("low_signal")

    tags = sorted(set(tags))
    return score, tags


def derive_problem_summary(post: RedditPost) -> str:
    """Extract a short pain-focused summary sentence.

    Args:
        post: Source Reddit post with title/body content.

    Returns:
        A short summary string (max 220 chars) representing the problem.
    """

    text = post.selftext.strip()
    if not text:
        return post.title[:220]
    sentences = re.split(r"[.!?\n]+", text)
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        lower_s = s.lower()
        if _contains_any(lower_s, PAIN_SIGNALS):
            return s[:220]
    first = sentences[0].strip() if sentences else ""
    return first[:220] if first else post.title[:220]


def derive_solution_hint(post: RedditPost, tags: list[str]) -> str:
    """Generate a lightweight monetizable solution direction.

    Args:
        post: Source Reddit post used for context keywords.
        tags: Heuristic tags produced by ``score_post``.

    Returns:
        A concise string with a suggested product/tool direction.
    """

    text = f"{post.title}\n{post.selftext}".lower()
    if "monetization" in tags:
        return "Test a lightweight SaaS or template product with recurring pricing."
    if _contains_any(text, ["freelance", "client", "proposal", "invoice"]):
        return "Build a workflow helper for freelancers with automation and reporting."
    if _contains_any(text, ["vibe coding", "coding agent", "prompt", "ai tool"]):
        return "Create an AI-assisted coding utility focused on one repetitive task."
    if _contains_any(text, ["team", "manager", "meeting", "calendar"]):
        return "Package this pain point into a micro-tool that reduces daily coordination work."
    return "Validate demand with a small automation tool and a narrow landing page."


def summarize_themes(ideas: list[IdeaCandidate]) -> list[tuple[str, int]]:
    """Aggregate reason-tag frequencies across ideas.

    Args:
        ideas: Extracted idea candidates.

    Returns:
        List of ``(tag, count)`` tuples sorted by most common first.
    """

    counts = Counter()
    for idea in ideas:
        for tag in idea.reason_tags:
            counts[tag] += 1
    return counts.most_common()


def _contains_any(text: str, patterns: list[str]) -> bool:
    """Check whether any substring pattern appears in text.

    Args:
        text: Lowercased source text to scan.
        patterns: Substring patterns to match.

    Returns:
        True if any pattern is present, otherwise False.
    """

    return any(pattern in text for pattern in patterns)


def _keyword_hits(text: str, keywords: list[str]) -> int:
    """Count keyword matches in text.

    Args:
        text: Lowercased source text to scan.
        keywords: Keywords from configuration.

    Returns:
        Number of keywords found in ``text``.
    """

    return sum(1 for keyword in keywords if keyword.lower() in text)


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words.

    Args:
        text: Input string to tokenize.

    Returns:
        List of lowercase token strings.
    """

    return WORD_RE.findall(text.lower())
