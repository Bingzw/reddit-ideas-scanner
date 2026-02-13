# Reddit Ideas Scanner (Option A)

Lightweight CLI + scheduler pipeline to scan selected subreddits and extract:
- passive-income opportunities
- tool/app/website ideas solving daily pain points

Default focus subreddits:
- `r/vibecoding`
- `r/AppIdeas`
- `r/freelance`
- `r/passive_income`
- `r/AI_Agents`
- `r/AgentsOfAI`
- `r/AiBuilders`
- `r/AIAssisted`
- `r/startups`
- `r/startup`
- `r/Startup_Ideas`
- `r/indiehackers`
- `r/buildinpublic`
- `r/scaleinpublic`
- `r/roastmystartup`
- `r/ShowMeYourSaaS`
- `r/SaaS`
- `r/saasbuild`
- `r/SaasDevelopers`
- `r/SaaSMarketing`
- `r/micro_saas`
- `r/microsaas`

## What this project does

1. Fetches latest Reddit posts from configured subreddits.
2. Scores posts using relevance heuristics.
3. Stores posts/ideas in SQLite for dedupe/history.
4. Generates CSV output and daily/weekly Markdown reports.
5. Optionally pushes report summary to email or Telegram.
6. Uses incremental fetching: first run pulls up to the past 7 days; later runs within 7 days pull only since the last successful run.
7. Prevents duplicate sends: a second run on the same UTC day is skipped (no report/email).
8. Logs every run with status/stats/errors in SQLite (`run_logs` table).
9. Optionally enriches ranking with Gemini LLM scoring/summaries (default model target: `gemini-2.5-flash-lite`).

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Run once:

```powershell
python -m reddit_ideas.cli run-once --period daily
```

Send SMTP test email:

```powershell
python -m reddit_ideas.cli test-email
```

Show recent run logs:

```powershell
python -m reddit_ideas.cli show-runs --limit 20
```

Outputs:
- `output/ideas_daily_YYYYMMDD_HHMMSS.csv`
- `output/report_daily_YYYYMMDD_HHMMSS.md`
- `data/reddit_ideas.db`

When Gemini enrichment is enabled, CSV includes:
- `llm_profit_score`
- `llm_confidence`

## Configuration

Create `config.toml` (optional). Env vars always override `config.toml`.

```toml
subreddits = [
  "vibecoding",
  "AppIdeas",
  "freelance",
  "passive_income",
  "AI_Agents",
  "AgentsOfAI",
  "AiBuilders",
  "AIAssisted",
  "startups",
  "startup",
  "Startup_Ideas",
  "indiehackers",
  "buildinpublic",
  "scaleinpublic",
  "roastmystartup",
  "ShowMeYourSaaS",
  "SaaS",
  "saasbuild",
  "SaasDevelopers",
  "SaaSMarketing",
  "micro_saas",
  "microsaas",
]
lookback_hours = 168
max_posts_per_subreddit = 75
min_score = 2.0
report_top_n = 15
data_dir = "data"
output_dir = "output"
user_agent = "reddit-ideas-scanner/0.1"

include_keywords = [
  "problem",
  "frustrat",
  "manual",
  "automate",
  "workflow",
  "saas",
  "tool",
  "app",
  "website",
  "passive income",
  "side hustle",
]

exclude_keywords = ["hiring", "looking for work", "resume review"]

[smtp]
# host = "smtp.gmail.com"
# port = 587
# user = "you@example.com"
# password = "app-password"
# email_to = "you@example.com"

[telegram]
# bot_token = "123456:ABCDEF..."
# chat_id = "123456789"

[gemini]
# enabled = true
# api_key = "your_google_ai_studio_key"
# model = "gemini-2.5-flash-lite"
# temperature = 0.2
# max_candidates = 40
# timeout_seconds = 25
```

`gemini-2.5-flash-lite` is the default low-cost/free-tier target model for LLM assessment.

## Scheduling

### Linux cron (daily at 08:00)

```bash
0 8 * * * cd /path/to/reddit_ideas && /path/to/python -m reddit_ideas.cli run-once --period daily
```

### Windows Task Scheduler

Use `scripts/run_daily.ps1` with your Python path and project path.

## Testing

```powershell
python -m unittest discover -s tests -v
```

Tests are local and do not call the live Reddit API.
