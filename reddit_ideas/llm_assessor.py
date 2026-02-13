from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .config import AppConfig, GeminiConfig
from .models import IdeaCandidate, RedditPost


@dataclass(slots=True)
class GeminiAssessment:
    profit_score: float
    confidence: float
    summary: str
    monetization_hint: str
    reason_tags: list[str]


class GeminiAssessor:
    def __init__(self, config: GeminiConfig, max_retries: int = 3) -> None:
        self.config = config
        self.max_retries = max_retries

    def assess(self, post: RedditPost, idea: IdeaCandidate) -> GeminiAssessment | None:
        prompt = _build_prompt(post, idea)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "responseMimeType": "application/json",
            },
        }
        response = self._generate_content(payload)
        content_text = _extract_response_text(response)
        if not content_text:
            return None

        parsed = _safe_parse_json(content_text)
        if parsed is None:
            return None

        profit_score = _clamp_float(parsed.get("profit_score"), 0.0, 100.0, fallback=50.0)
        confidence = _clamp_float(parsed.get("confidence"), 0.0, 1.0, fallback=0.5)
        summary = str(parsed.get("summary", "")).strip()[:240]
        monetization_hint = str(parsed.get("monetization_hint", "")).strip()[:220]
        reason_tags = _normalize_reason_tags(parsed.get("reason_tags"))

        return GeminiAssessment(
            profit_score=profit_score,
            confidence=confidence,
            summary=summary,
            monetization_hint=monetization_hint,
            reason_tags=reason_tags,
        )

    def _generate_content(self, payload: dict) -> dict:
        encoded_model = urllib.parse.quote(self.config.model, safe="")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{encoded_model}:generateContent"
            f"?key={urllib.parse.quote(self.config.api_key, safe='')}"
        )
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.2 * attempt)
        if last_error is None:
            raise RuntimeError("Gemini request failed with unknown error.")
        raise RuntimeError("Gemini request failed.") from last_error


def enrich_ideas_with_gemini(
    ideas: list[IdeaCandidate],
    posts: list[RedditPost],
    config: AppConfig,
    assessor: GeminiAssessor | None = None,
) -> list[IdeaCandidate]:
    if not ideas or config.gemini is None or not config.gemini.enabled:
        return ideas

    post_by_id = {post.post_id: post for post in posts}
    sorted_ideas = sorted(ideas, key=lambda item: item.relevance_score, reverse=True)
    assess_limit = max(config.gemini.max_candidates, 1)
    target_ideas = sorted_ideas[:assess_limit]

    effective_assessor = assessor or GeminiAssessor(config=config.gemini)
    for idea in target_ideas:
        post = post_by_id.get(idea.post_id)
        if post is None:
            continue
        assessment = effective_assessor.assess(post=post, idea=idea)
        if assessment is None:
            continue

        if assessment.summary:
            idea.problem_summary = assessment.summary
        if assessment.monetization_hint:
            idea.solution_hint = assessment.monetization_hint

        idea.llm_profit_score = round(assessment.profit_score, 2)
        idea.llm_confidence = round(assessment.confidence, 3)
        idea.relevance_score = round(
            (idea.relevance_score * 0.35) + ((assessment.profit_score / 10.0) * 0.65), 3
        )

        reason_tags = set(idea.reason_tags)
        reason_tags.add("llm_assessed")
        reason_tags.update(assessment.reason_tags)
        idea.reason_tags = sorted(reason_tags)

    sorted_ideas.sort(key=lambda item: item.relevance_score, reverse=True)
    return sorted_ideas


def _build_prompt(post: RedditPost, idea: IdeaCandidate) -> str:
    body = post.selftext.strip()
    if len(body) > 2500:
        body = body[:2500]

    return (
        "You are evaluating startup ideas from Reddit posts.\n"
        "Goal: estimate likelihood this can become a profitable small business that solves real user pain.\n"
        "Return ONLY strict JSON with keys:\n"
        "- profit_score: number 0-100 (higher means better business potential)\n"
        "- confidence: number 0-1\n"
        "- summary: short 1-2 sentence problem summary\n"
        "- monetization_hint: one concise monetization direction\n"
        "- reason_tags: array of up to 3 short snake_case tags\n\n"
        f"Subreddit: r/{post.subreddit}\n"
        f"Title: {post.title}\n"
        f"Body: {body}\n"
        f"Heuristic score: {idea.relevance_score}\n"
        f"Heuristic tags: {', '.join(idea.reason_tags)}\n"
    )


def _extract_response_text(response: dict) -> str:
    candidates = response.get("candidates", [])
    if not candidates:
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts:
        return ""
    return str(parts[0].get("text", "")).strip()


def _safe_parse_json(value: str) -> dict | None:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"\{.*\}", value, flags=re.DOTALL)
    if fenced_match:
        try:
            parsed = json.loads(fenced_match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _normalize_reason_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for item in value[:3]:
        tag = str(item).strip().lower().replace(" ", "_")
        tag = re.sub(r"[^a-z0-9_]+", "", tag)
        if tag:
            tags.append(f"llm_{tag[:24]}")
    return sorted(set(tags))


def _clamp_float(value: object, minimum: float, maximum: float, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(min(parsed, maximum), minimum)
