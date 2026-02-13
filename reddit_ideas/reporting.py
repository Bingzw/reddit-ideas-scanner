from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .models import IdeaCandidate


def export_ideas_csv(ideas: list[IdeaCandidate], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "post_id",
                "subreddit",
                "title",
                "problem_summary",
                "solution_hint",
                "relevance_score",
                "reason_tags",
                "created_utc",
                "permalink",
                "url",
                "author",
                "num_comments",
                "upvotes",
                "llm_profit_score",
                "llm_confidence",
            ]
        )
        for idea in ideas:
            writer.writerow(
                [
                    idea.post_id,
                    idea.subreddit,
                    idea.title,
                    idea.problem_summary,
                    idea.solution_hint,
                    idea.relevance_score,
                    ",".join(idea.reason_tags),
                    idea.created_utc,
                    idea.permalink,
                    idea.url,
                    idea.author,
                    idea.num_comments,
                    idea.upvotes,
                    idea.llm_profit_score if idea.llm_profit_score is not None else "",
                    idea.llm_confidence if idea.llm_confidence is not None else "",
                ]
            )


def build_markdown_report(
    ideas: list[IdeaCandidate], period: str, generated_at: datetime, top_n: int
) -> str:
    top_ideas = ideas[: max(top_n, 1)]
    by_subreddit = Counter(idea.subreddit for idea in ideas)
    by_tag = Counter(tag for idea in ideas for tag in idea.reason_tags)

    lines: list[str] = []
    lines.append(f"# Reddit Idea Scanner Report ({period.title()})")
    lines.append("")
    lines.append(f"Generated at: {generated_at.astimezone(UTC).isoformat()}")
    lines.append(f"Total ideas in window: {len(ideas)}")
    lines.append("")
    lines.append("## Top Opportunities")
    lines.append("")

    if not top_ideas:
        lines.append("No ideas met the threshold in this period.")
    else:
        for index, idea in enumerate(top_ideas, start=1):
            created_at = datetime.fromtimestamp(idea.created_utc, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
            lines.append(
                f"{index}. [{idea.title}]({idea.permalink}) "
                f"(r/{idea.subreddit}, score={idea.relevance_score:.2f}, {created_at})"
            )
            lines.append(f"Problem: {idea.problem_summary}")
            lines.append(f"Hint: {idea.solution_hint}")
            lines.append(f"Signals: {', '.join(idea.reason_tags)}")
            if idea.llm_profit_score is not None:
                confidence = (
                    f", confidence={idea.llm_confidence:.2f}"
                    if idea.llm_confidence is not None
                    else ""
                )
                lines.append(f"LLM Profit Score: {idea.llm_profit_score:.1f}/100{confidence}")
            lines.append("")

    lines.append("## Subreddit Distribution")
    lines.append("")
    if by_subreddit:
        for subreddit, count in by_subreddit.most_common():
            lines.append(f"- r/{subreddit}: {count}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Signal Distribution")
    lines.append("")
    if by_tag:
        for tag, count in by_tag.most_common():
            lines.append(f"- {tag}: {count}")
    else:
        lines.append("- None")
    lines.append("")

    return "\n".join(lines)


def write_text_report(report_content: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report_content, encoding="utf-8")
