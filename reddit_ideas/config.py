from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SUBREDDITS = [
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
DEFAULT_KEYWORDS = [
    "problem",
    "frustrat",
    "manual",
    "automate",
    "time-consuming",
    "workflow",
    "template",
    "saas",
    "tool",
    "app",
    "website",
    "plugin",
    "extension",
    "side hustle",
    "passive income",
    "subscription",
]
DEFAULT_EXCLUDE_KEYWORDS = ["hiring", "looking for work", "upwork profile", "resume review"]


@dataclass(slots=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    email_to: str


@dataclass(slots=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass(slots=True)
class GeminiConfig:
    enabled: bool
    api_key: str
    model: str
    temperature: float
    max_candidates: int
    timeout_seconds: int


@dataclass(slots=True)
class AppConfig:
    subreddits: list[str]
    lookback_hours: int
    max_posts_per_subreddit: int
    min_score: float
    report_top_n: int
    data_dir: Path
    output_dir: Path
    user_agent: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    smtp: SmtpConfig | None
    telegram: TelegramConfig | None
    gemini: GeminiConfig | None


def _csv_to_list(value: str | list[str] | None, default: list[str]) -> list[str]:
    if value is None:
        return default.copy()
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    return [item.strip() for item in value.split(",") if item and item.strip()]


def _int_env(name: str, fallback: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


def _float_env(name: str, fallback: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def _bool_env(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _bool_value(value: object, fallback: bool) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(value, int):
        return value != 0
    return fallback


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_config(config_path: Path | None = None) -> AppConfig:
    file_path = config_path or Path("config.toml")
    raw = _read_toml(file_path)

    subreddits = _csv_to_list(
        os.getenv("REDDIT_IDEAS_SUBREDDITS", raw.get("subreddits")), DEFAULT_SUBREDDITS
    )
    include_keywords = _csv_to_list(
        os.getenv("REDDIT_IDEAS_INCLUDE_KEYWORDS", raw.get("include_keywords")), DEFAULT_KEYWORDS
    )
    exclude_keywords = _csv_to_list(
        os.getenv("REDDIT_IDEAS_EXCLUDE_KEYWORDS", raw.get("exclude_keywords")),
        DEFAULT_EXCLUDE_KEYWORDS,
    )

    lookback_hours = _int_env("REDDIT_IDEAS_LOOKBACK_HOURS", int(raw.get("lookback_hours", 168)))
    max_posts = _int_env(
        "REDDIT_IDEAS_MAX_POSTS_PER_SUB", int(raw.get("max_posts_per_subreddit", 75))
    )
    min_score = _float_env("REDDIT_IDEAS_MIN_SCORE", float(raw.get("min_score", 2.0)))
    report_top_n = _int_env("REDDIT_IDEAS_REPORT_TOP_N", int(raw.get("report_top_n", 15)))

    data_dir = Path(os.getenv("REDDIT_IDEAS_DATA_DIR", raw.get("data_dir", "data")))
    output_dir = Path(os.getenv("REDDIT_IDEAS_OUTPUT_DIR", raw.get("output_dir", "output")))
    user_agent = os.getenv(
        "REDDIT_IDEAS_USER_AGENT", raw.get("user_agent", "reddit-ideas-scanner/0.1")
    )

    smtp: SmtpConfig | None = None
    smtp_section = raw.get("smtp", {})
    smtp_host = os.getenv("REDDIT_IDEAS_SMTP_HOST", smtp_section.get("host", ""))
    smtp_user = os.getenv("REDDIT_IDEAS_SMTP_USER", smtp_section.get("user", ""))
    smtp_password = os.getenv("REDDIT_IDEAS_SMTP_PASSWORD", smtp_section.get("password", ""))
    smtp_to = os.getenv("REDDIT_IDEAS_EMAIL_TO", smtp_section.get("email_to", ""))
    smtp_port = _int_env("REDDIT_IDEAS_SMTP_PORT", int(smtp_section.get("port", 587)))
    if smtp_host and smtp_user and smtp_password and smtp_to:
        smtp = SmtpConfig(
            host=smtp_host,
            port=smtp_port,
            user=smtp_user,
            password=smtp_password,
            email_to=smtp_to,
        )

    telegram: TelegramConfig | None = None
    tg_section = raw.get("telegram", {})
    tg_token = os.getenv("REDDIT_IDEAS_TELEGRAM_BOT_TOKEN", tg_section.get("bot_token", ""))
    tg_chat_id = os.getenv("REDDIT_IDEAS_TELEGRAM_CHAT_ID", tg_section.get("chat_id", ""))
    if tg_token and tg_chat_id:
        telegram = TelegramConfig(bot_token=tg_token, chat_id=tg_chat_id)

    gemini: GeminiConfig | None = None
    gemini_section = raw.get("gemini", {})
    gemini_enabled = _bool_env(
        "REDDIT_IDEAS_GEMINI_ENABLED", _bool_value(gemini_section.get("enabled"), False)
    )
    gemini_api_key = os.getenv("REDDIT_IDEAS_GEMINI_API_KEY", gemini_section.get("api_key", ""))
    gemini_model = os.getenv(
        "REDDIT_IDEAS_GEMINI_MODEL", gemini_section.get("model", "gemini-2.5-flash-lite")
    )
    gemini_temperature = _float_env(
        "REDDIT_IDEAS_GEMINI_TEMPERATURE", float(gemini_section.get("temperature", 0.2))
    )
    gemini_max_candidates = _int_env(
        "REDDIT_IDEAS_GEMINI_MAX_CANDIDATES", int(gemini_section.get("max_candidates", 40))
    )
    gemini_timeout_seconds = _int_env(
        "REDDIT_IDEAS_GEMINI_TIMEOUT_SECONDS", int(gemini_section.get("timeout_seconds", 25))
    )
    if gemini_enabled and gemini_api_key:
        gemini = GeminiConfig(
            enabled=True,
            api_key=gemini_api_key,
            model=gemini_model,
            temperature=gemini_temperature,
            max_candidates=gemini_max_candidates,
            timeout_seconds=gemini_timeout_seconds,
        )

    return AppConfig(
        subreddits=subreddits,
        lookback_hours=lookback_hours,
        max_posts_per_subreddit=max_posts,
        min_score=min_score,
        report_top_n=report_top_n,
        data_dir=data_dir,
        output_dir=output_dir,
        user_agent=user_agent,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
        smtp=smtp,
        telegram=telegram,
        gemini=gemini,
    )
