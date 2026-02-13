from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import AppConfig
from .extractor import extract_ideas
from .notifiers import Notifier, build_notifier
from .reddit_client import RedditClient
from .reporting import build_markdown_report, export_ideas_csv, write_text_report
from .storage import Storage


@dataclass(slots=True)
class RunResult:
    status: str
    fetched_posts: int
    extracted_ideas: int
    window_ideas: int
    started_utc: int
    finished_utc: int
    csv_path: Path | None
    report_path: Path | None
    email_sent: bool
    message: str


def run_once(
    config: AppConfig,
    period: str = "daily",
    reddit_client: RedditClient | None = None,
    notifier: Notifier | None = None,
    now: datetime | None = None,
) -> RunResult:
    period = period.lower().strip()
    if period not in {"daily", "weekly"}:
        raise ValueError("period must be either 'daily' or 'weekly'")

    runtime = now or datetime.now(tz=UTC)
    started_utc = int(runtime.timestamp())
    run_day_utc = runtime.strftime("%Y-%m-%d")
    lookback_seconds = max(config.lookback_hours, 1) * 60 * 60
    default_lookback_floor = started_utc - lookback_seconds

    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    storage = Storage(config.data_dir / "reddit_ideas.db")
    run_id = storage.start_run(period=period, run_day_utc=run_day_utc, run_started_utc=started_utc)

    if storage.has_successful_run_on_day(period=period, run_day_utc=run_day_utc):
        finished_utc = int((now or datetime.now(tz=UTC)).timestamp())
        message = f"Skipped duplicate {period} run for UTC day {run_day_utc}."
        storage.finish_run(
            run_id=run_id,
            status="skipped_same_day",
            run_finished_utc=finished_utc,
            fetched_posts=0,
            extracted_ideas=0,
            window_ideas=0,
            email_sent=False,
            message=message,
        )
        return RunResult(
            status="skipped_same_day",
            fetched_posts=0,
            extracted_ideas=0,
            window_ideas=0,
            started_utc=started_utc,
            finished_utc=finished_utc,
            csv_path=None,
            report_path=None,
            email_sent=False,
            message=message,
        )

    latest_success = storage.get_latest_successful_run(period=period)
    lookback_floor = default_lookback_floor
    if latest_success and latest_success.run_finished_utc is not None:
        seconds_since_last_success = started_utc - latest_success.run_finished_utc
        if seconds_since_last_success <= lookback_seconds:
            lookback_floor = latest_success.run_finished_utc

    client = reddit_client or RedditClient(user_agent=config.user_agent)
    email_sent = False

    try:
        posts = []
        for subreddit in config.subreddits:
            fetched = client.fetch_new_posts_since(
                subreddit=subreddit,
                since_utc=lookback_floor,
                max_posts=config.max_posts_per_subreddit,
            )
            posts.extend(fetched)

        storage.upsert_posts(posts=posts, fetched_utc=started_utc)
        ideas = extract_ideas(posts=posts, config=config)
        storage.upsert_ideas(ideas=ideas, extracted_utc=started_utc)

        window_ideas = storage.get_ideas_since(lookback_floor)
        date_stamp = runtime.strftime("%Y%m%d_%H%M%S")
        csv_path = config.output_dir / f"ideas_{period}_{date_stamp}.csv"
        report_path = config.output_dir / f"report_{period}_{date_stamp}.md"

        export_ideas_csv(window_ideas, csv_path)
        report_text = build_markdown_report(
            ideas=window_ideas, period=period, generated_at=runtime, top_n=config.report_top_n
        )
        write_text_report(report_text, report_path)

        effective_notifier = notifier or build_notifier(config)
        if effective_notifier is not None:
            summary = (
                f"Collected ideas since {datetime.fromtimestamp(lookback_floor, tz=UTC).isoformat()}.\n"
                f"Posts checked: {len(posts)}.\n"
                f"Newly extracted in this run: {len(ideas)}.\n"
                f"Report: {report_path.name}"
            )
            effective_notifier.send(
                subject=f"Reddit Ideas {period.title()} Report",
                body=summary,
                report_path=report_path,
            )
            email_sent = True

        finished_utc = int((now or datetime.now(tz=UTC)).timestamp())
        message = (
            "Success. Lookback started at "
            + datetime.fromtimestamp(lookback_floor, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        storage.finish_run(
            run_id=run_id,
            status="success",
            run_finished_utc=finished_utc,
            fetched_posts=len(posts),
            extracted_ideas=len(ideas),
            window_ideas=len(window_ideas),
            email_sent=email_sent,
            message=message,
        )
        return RunResult(
            status="success",
            fetched_posts=len(posts),
            extracted_ideas=len(ideas),
            window_ideas=len(window_ideas),
            started_utc=started_utc,
            finished_utc=finished_utc,
            csv_path=csv_path,
            report_path=report_path,
            email_sent=email_sent,
            message=message,
        )
    except Exception as exc:
        finished_utc = int((now or datetime.now(tz=UTC)).timestamp())
        message = f"{type(exc).__name__}: {exc}"
        storage.finish_run(
            run_id=run_id,
            status="failed",
            run_finished_utc=finished_utc,
            fetched_posts=0,
            extracted_ideas=0,
            window_ideas=0,
            email_sent=False,
            message=message,
        )
        raise
