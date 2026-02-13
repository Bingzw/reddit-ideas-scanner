# Project Milestones

## Milestone 1: CLI Pipeline Scaffold
- Status: Completed on 2026-02-12
- Scope:
  - Added Python package scaffold for a scheduled Reddit scanner.
  - Implemented config loading from `config.toml` and environment variables.
  - Set default subreddits to `vibecoding`, `AppIdeas`, `freelance`, `passive_income`.
- Deliverables:
  - `reddit_ideas/cli.py`
  - `reddit_ideas/config.py`
  - `pyproject.toml`
  - `README.md`

## Milestone 2: Reddit Ingestion + Idea Extraction
- Status: Completed on 2026-02-12
- Scope:
  - Implemented public Reddit JSON ingestion (`/new.json`) with retry logic.
  - Added heuristic scoring for passive-income and tool/app opportunity signals.
  - Added summary/hint generation for shortlisted ideas.
- Deliverables:
  - `reddit_ideas/reddit_client.py`
  - `reddit_ideas/extractor.py`
  - `reddit_ideas/models.py`

## Milestone 3: Storage + Reporting + Notification
- Status: Completed on 2026-02-12
- Scope:
  - Added SQLite persistence for posts and extracted ideas.
  - Added CSV export and daily/weekly Markdown reporting.
  - Added optional email and Telegram notification adapters.
- Deliverables:
  - `reddit_ideas/storage.py`
  - `reddit_ideas/reporting.py`
  - `reddit_ideas/notifiers.py`
  - `reddit_ideas/pipeline.py`

## Milestone 4: Test Coverage + Ops Script
- Status: Completed on 2026-02-12
- Scope:
  - Unit tests for extraction and reporting.
  - Integration-style pipeline test with mocked client/notifier.
  - Windows daily run script for Task Scheduler.
- Deliverables:
  - `tests/test_extractor.py`
  - `tests/test_notifiers.py`
  - `tests/test_cli.py`
  - `tests/test_reporting.py`
  - `tests/test_pipeline.py`
  - `scripts/run_daily.ps1`
- Verification:
  - `python -m unittest discover -s tests -v` passed (7 tests).
  - Live run passed:
    - `python -m reddit_ideas.cli run-once --period daily`
    - generated `output/ideas_daily_20260212_063331.csv`
    - generated `output/report_daily_20260212_063331.md`

## Milestone 5: Incremental 7-Day Collection + Run Logging
- Status: Completed on 2026-02-13
- Scope:
  - Expanded default subreddit list with startup/SaaS/AI-agent communities.
  - Added incremental ingestion:
    - first run pulls up to the previous 7 days (`lookback_hours=168`)
    - subsequent runs inside that window pull only since last successful run
  - Added same-day idempotency:
    - duplicate run on the same UTC day is skipped
    - skipped run returns no report paths and sends no email
  - Added run lifecycle logging in SQLite:
    - start/end time
    - status (`success`, `failed`, `skipped_same_day`)
    - fetched posts, extracted ideas, window ideas
    - email sent flag
    - message/error text
  - Added `show-runs` CLI command to inspect logs quickly.
- Deliverables:
  - `reddit_ideas/config.py`
  - `reddit_ideas/reddit_client.py`
  - `reddit_ideas/storage.py`
  - `reddit_ideas/pipeline.py`
  - `reddit_ideas/cli.py`
  - `tests/test_pipeline.py`
  - `README.md`
  - `.env.example`
  - `config.toml.example`
- Verification:
  - `python -m unittest discover -s tests -v` passed (9 tests).
  - `python -m compileall reddit_ideas tests` passed.
  - `python -m reddit_ideas.cli --help` shows `show-runs`.

## Blockers and Resolutions
- Blocker: SQLite DB file lock on Windows during temporary-directory cleanup in integration test.
- Blocker: GitHub push authentication failed (`Invalid username or token`) and `gh` CLI is not installed in this environment.
- Resolution log:
  - 2026-02-12: Repo had no starter files; created full initial implementation scaffold from scratch.
  - 2026-02-12: Added explicit connection lifecycle management in `reddit_ideas/storage.py` so each DB call closes handles deterministically.
  - 2026-02-12: Added `test-email` CLI probe to validate SMTP credentials without running a full Reddit scan.
  - 2026-02-13: Needed deterministic timestamps for incremental-run tests; resolved by honoring injected `now` for both start and finish timestamps in pipeline tests.
  - 2026-02-13: Initialized local git repo, added `.gitignore` rule for `config.toml`, committed code, and configured remote to `https://github.com/Bingzw/reddit-ideas-scanner.git`; pending PAT/CLI auth to complete first push.
