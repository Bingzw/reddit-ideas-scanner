from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .models import IdeaCandidate, RedditPost


@dataclass(slots=True)
class RunLog:
    run_id: int
    period: str
    run_day_utc: str
    run_started_utc: int
    run_finished_utc: int | None
    status: str
    fetched_posts: int
    extracted_ideas: int
    window_ideas: int
    email_sent: bool
    message: str


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    post_id TEXT PRIMARY KEY,
                    subreddit TEXT NOT NULL,
                    title TEXT NOT NULL,
                    selftext TEXT NOT NULL,
                    permalink TEXT NOT NULL,
                    url TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_utc INTEGER NOT NULL,
                    num_comments INTEGER NOT NULL,
                    upvotes INTEGER NOT NULL,
                    is_self INTEGER NOT NULL,
                    fetched_utc INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ideas (
                    post_id TEXT PRIMARY KEY,
                    subreddit TEXT NOT NULL,
                    title TEXT NOT NULL,
                    problem_summary TEXT NOT NULL,
                    solution_hint TEXT NOT NULL,
                    relevance_score REAL NOT NULL,
                    reason_tags TEXT NOT NULL,
                    created_utc INTEGER NOT NULL,
                    permalink TEXT NOT NULL,
                    url TEXT NOT NULL,
                    author TEXT NOT NULL,
                    num_comments INTEGER NOT NULL,
                    upvotes INTEGER NOT NULL,
                    llm_profit_score REAL,
                    llm_confidence REAL,
                    extracted_utc INTEGER NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                );

                CREATE TABLE IF NOT EXISTS run_logs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    run_day_utc TEXT NOT NULL,
                    run_started_utc INTEGER NOT NULL,
                    run_finished_utc INTEGER,
                    status TEXT NOT NULL,
                    fetched_posts INTEGER NOT NULL DEFAULT 0,
                    extracted_ideas INTEGER NOT NULL DEFAULT 0,
                    window_ideas INTEGER NOT NULL DEFAULT 0,
                    email_sent INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_run_logs_period_started
                ON run_logs(period, run_started_utc DESC);
                """
            )
            self._ensure_ideas_columns(conn)
            conn.commit()

    def _ensure_ideas_columns(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(ideas);").fetchall()
        existing = {row["name"] for row in rows}
        if "llm_profit_score" not in existing:
            conn.execute("ALTER TABLE ideas ADD COLUMN llm_profit_score REAL;")
        if "llm_confidence" not in existing:
            conn.execute("ALTER TABLE ideas ADD COLUMN llm_confidence REAL;")

    def upsert_posts(self, posts: list[RedditPost], fetched_utc: int) -> None:
        if not posts:
            return
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO posts (
                    post_id, subreddit, title, selftext, permalink, url, author,
                    created_utc, num_comments, upvotes, is_self, fetched_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(post_id) DO UPDATE SET
                    subreddit=excluded.subreddit,
                    title=excluded.title,
                    selftext=excluded.selftext,
                    permalink=excluded.permalink,
                    url=excluded.url,
                    author=excluded.author,
                    created_utc=excluded.created_utc,
                    num_comments=excluded.num_comments,
                    upvotes=excluded.upvotes,
                    is_self=excluded.is_self,
                    fetched_utc=excluded.fetched_utc;
                """,
                [
                    (
                        post.post_id,
                        post.subreddit,
                        post.title,
                        post.selftext,
                        post.permalink,
                        post.url,
                        post.author,
                        post.created_utc,
                        post.num_comments,
                        post.upvotes,
                        1 if post.is_self else 0,
                        fetched_utc,
                    )
                    for post in posts
                ],
            )
            conn.commit()

    def upsert_ideas(self, ideas: list[IdeaCandidate], extracted_utc: int) -> None:
        if not ideas:
            return
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO ideas (
                    post_id, subreddit, title, problem_summary, solution_hint, relevance_score,
                    reason_tags, created_utc, permalink, url, author, num_comments, upvotes,
                    llm_profit_score, llm_confidence, extracted_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(post_id) DO UPDATE SET
                    subreddit=excluded.subreddit,
                    title=excluded.title,
                    problem_summary=excluded.problem_summary,
                    solution_hint=excluded.solution_hint,
                    relevance_score=excluded.relevance_score,
                    reason_tags=excluded.reason_tags,
                    created_utc=excluded.created_utc,
                    permalink=excluded.permalink,
                    url=excluded.url,
                    author=excluded.author,
                    num_comments=excluded.num_comments,
                    upvotes=excluded.upvotes,
                    llm_profit_score=excluded.llm_profit_score,
                    llm_confidence=excluded.llm_confidence,
                    extracted_utc=excluded.extracted_utc;
                """,
                [
                    (
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
                        idea.llm_profit_score,
                        idea.llm_confidence,
                        extracted_utc,
                    )
                    for idea in ideas
                ],
            )
            conn.commit()

    def get_ideas_since(self, created_utc_floor: int) -> list[IdeaCandidate]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT post_id, subreddit, title, problem_summary, solution_hint, relevance_score,
                       reason_tags, created_utc, permalink, url, author, num_comments, upvotes,
                       llm_profit_score, llm_confidence
                FROM ideas
                WHERE created_utc >= ?
                ORDER BY relevance_score DESC, created_utc DESC;
                """,
                (created_utc_floor,),
            ).fetchall()

        ideas: list[IdeaCandidate] = []
        for row in rows:
            tags = [tag for tag in row["reason_tags"].split(",") if tag]
            ideas.append(
                IdeaCandidate(
                    post_id=row["post_id"],
                    subreddit=row["subreddit"],
                    title=row["title"],
                    problem_summary=row["problem_summary"],
                    solution_hint=row["solution_hint"],
                    relevance_score=float(row["relevance_score"]),
                    reason_tags=tags,
                    created_utc=int(row["created_utc"]),
                    permalink=row["permalink"],
                    url=row["url"],
                    author=row["author"],
                    num_comments=int(row["num_comments"]),
                    upvotes=int(row["upvotes"]),
                    llm_profit_score=float(row["llm_profit_score"])
                    if row["llm_profit_score"] is not None
                    else None,
                    llm_confidence=float(row["llm_confidence"])
                    if row["llm_confidence"] is not None
                    else None,
                )
            )
        return ideas

    def start_run(self, period: str, run_day_utc: str, run_started_utc: int) -> int:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO run_logs (
                    period, run_day_utc, run_started_utc, status
                ) VALUES (?, ?, ?, 'started');
                """,
                (period, run_day_utc, run_started_utc),
            )
            conn.commit()
            run_id = cursor.lastrowid
            if run_id is None:
                raise RuntimeError("Failed to create run log record.")
            return int(run_id)

    def finish_run(
        self,
        run_id: int,
        status: str,
        run_finished_utc: int,
        fetched_posts: int,
        extracted_ideas: int,
        window_ideas: int,
        email_sent: bool,
        message: str = "",
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE run_logs
                SET run_finished_utc = ?,
                    status = ?,
                    fetched_posts = ?,
                    extracted_ideas = ?,
                    window_ideas = ?,
                    email_sent = ?,
                    message = ?
                WHERE run_id = ?;
                """,
                (
                    run_finished_utc,
                    status,
                    fetched_posts,
                    extracted_ideas,
                    window_ideas,
                    1 if email_sent else 0,
                    message,
                    run_id,
                ),
            )
            conn.commit()

    def has_successful_run_on_day(self, period: str, run_day_utc: str) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM run_logs
                WHERE period = ? AND run_day_utc = ? AND status = 'success'
                LIMIT 1;
                """,
                (period, run_day_utc),
            ).fetchone()
        return row is not None

    def get_latest_successful_run(self, period: str) -> RunLog | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT run_id, period, run_day_utc, run_started_utc, run_finished_utc, status,
                       fetched_posts, extracted_ideas, window_ideas, email_sent, message
                FROM run_logs
                WHERE period = ? AND status = 'success'
                ORDER BY run_finished_utc DESC, run_started_utc DESC
                LIMIT 1;
                """,
                (period,),
            ).fetchone()
        if row is None:
            return None
        return RunLog(
            run_id=int(row["run_id"]),
            period=row["period"],
            run_day_utc=row["run_day_utc"],
            run_started_utc=int(row["run_started_utc"]),
            run_finished_utc=int(row["run_finished_utc"]) if row["run_finished_utc"] else None,
            status=row["status"],
            fetched_posts=int(row["fetched_posts"]),
            extracted_ideas=int(row["extracted_ideas"]),
            window_ideas=int(row["window_ideas"]),
            email_sent=bool(row["email_sent"]),
            message=row["message"] or "",
        )

    def list_run_logs(self, limit: int = 20) -> list[RunLog]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT run_id, period, run_day_utc, run_started_utc, run_finished_utc, status,
                       fetched_posts, extracted_ideas, window_ideas, email_sent, message
                FROM run_logs
                ORDER BY run_started_utc DESC
                LIMIT ?;
                """,
                (max(limit, 1),),
            ).fetchall()

        logs: list[RunLog] = []
        for row in rows:
            logs.append(
                RunLog(
                    run_id=int(row["run_id"]),
                    period=row["period"],
                    run_day_utc=row["run_day_utc"],
                    run_started_utc=int(row["run_started_utc"]),
                    run_finished_utc=int(row["run_finished_utc"])
                    if row["run_finished_utc"]
                    else None,
                    status=row["status"],
                    fetched_posts=int(row["fetched_posts"]),
                    extracted_ideas=int(row["extracted_ideas"]),
                    window_ideas=int(row["window_ideas"]),
                    email_sent=bool(row["email_sent"]),
                    message=row["message"] or "",
                )
            )
        return logs
