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

## Milestone 6: Gemini LLM Profitability Enrichment
- Status: Completed on 2026-02-13
- Scope:
  - Added optional Gemini-based LLM enrichment focused on profitability likelihood.
  - Default LLM target model set to `gemini-2.5-flash-lite` (low-cost/free-tier oriented).
  - Integrated LLM outputs into ranking, summaries, CSV exports, markdown report, and SQLite schema.
  - Added deterministic tests for enrichment with a mocked assessor.
- Deliverables:
  - `reddit_ideas/llm_assessor.py`
  - `reddit_ideas/config.py`
  - `reddit_ideas/models.py`
  - `reddit_ideas/pipeline.py`
  - `reddit_ideas/storage.py`
  - `reddit_ideas/reporting.py`
  - `tests/test_llm_assessor.py`
  - `tests/test_cli.py`
  - `tests/test_extractor.py`
  - `tests/test_pipeline.py`
  - `tests/test_reporting.py`
  - `.env.example`
  - `config.toml.example`
  - `README.md`
- Verification:
  - `python -m unittest discover -s tests -v` passed (10 tests).
  - `python -m compileall reddit_ideas tests` passed.
  - `python -m reddit_ideas.cli --config config.toml.example run-once --period daily` runs and preserves same-day skip behavior.

## Milestone 7: Gemini Rate-Limit Fixes + Pipeline Resilience
- Status: Completed on 2026-02-28
- Scope:
  - Diagnosed that all LLM enrichment runs had failed silently since Milestone 6:
    0 of 1,534 stored ideas had ever received an LLM score.
  - Root cause: 40 back-to-back Gemini calls with no throttle exceeded the free-tier
    limit of 10 RPM and 20 RPD, causing HTTP 429 errors on ~call 15.
  - The 1.2s retry backoff was far too short to recover from a per-minute rate limit.
  - Added inter-call delay of 6.5s (60s ÷ 10 RPM + buffer) between consecutive calls.
  - Added explicit HTTP 429 handling with a 60s wait-and-retry instead of generic backoff.
  - Reduced `max_candidates` from 40 to 15 to stay within the 20 RPD daily quota.
  - Made `assess()` return `None` on error rather than raising, so one bad call
    no longer crashes the entire pipeline.
  - Added a circuit breaker: after 3 consecutive LLM failures the enrichment phase
    is skipped and the pipeline continues with heuristic scores only.
  - Added module-level docstrings and inline comments to all core modules.
- Deliverables:
  - `reddit_ideas/llm_assessor.py`
  - `reddit_ideas/extractor.py`
  - `reddit_ideas/pipeline.py`
  - `reddit_ideas/reddit_client.py`
  - `reddit_ideas/storage.py`
  - `reddit_ideas/notifiers.py`
  - `reddit_ideas/reporting.py`
  - `config.toml.example`
  - `PROJECT_MILESTONES.md`
- Verification:
  - `python -m pytest tests/test_llm_assessor.py -v` passed (1 test).
  - Live weekly run completed successfully:
    - `fetched_posts=1414, extracted_ideas=670, window_ideas=1052, email_sent=True`

## Milestone 8: Improved Email Content + Top-N Increase
- Status: Completed on 2026-02-28
- Scope:
  - Email body previously contained only a 4-line stats summary; the actual
    ideas were only accessible by opening the markdown attachment.
  - Added `build_email_body()` in `reporting.py` that renders the top-N ideas
    inline in the email body as clean plain text (no markdown syntax): title,
    subreddit, score, date, LLM profit score, problem summary, hint, signals,
    and direct Reddit link for each idea.
  - Updated `pipeline.py` to call `build_email_body()` with the full window
    ideas list, so the email body and attachment always stay in sync.
  - Increased `report_top_n` from 15 to 20 in config.
- Deliverables:
  - `reddit_ideas/reporting.py`
  - `reddit_ideas/pipeline.py`
  - `config.toml.example`
  - `PROJECT_MILESTONES.md`

## Blockers and Resolutions
- Blocker: SQLite DB file lock on Windows during temporary-directory cleanup in integration test.
- Blocker: GitHub push authentication failed (`Invalid username or token`) and `gh` CLI is not installed in this environment.
- Resolution log:
  - 2026-02-12: Repo had no starter files; created full initial implementation scaffold from scratch.
  - 2026-02-12: Added explicit connection lifecycle management in `reddit_ideas/storage.py` so each DB call closes handles deterministically.
  - 2026-02-12: Added `test-email` CLI probe to validate SMTP credentials without running a full Reddit scan.
  - 2026-02-13: Needed deterministic timestamps for incremental-run tests; resolved by honoring injected `now` for both start and finish timestamps in pipeline tests.
  - 2026-02-13: Initialized local git repo, added `.gitignore` rule for `config.toml`, and configured remote to `https://github.com/Bingzw/reddit-ideas-scanner.git`.
  - 2026-02-13: Resolved remote history/auth push issues; merged remote `main` history and pushed successfully to GitHub.
