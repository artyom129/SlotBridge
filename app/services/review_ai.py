from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import Settings


logger = logging.getLogger("slotbridge.review_ai")
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){7,15}(?!\d)")


def sanitize_comment(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _EMAIL.sub("[email removed]", value)
    cleaned = _PHONE.sub("[phone removed]", cleaned)
    return cleaned[:500]


def summarize_reviews(settings: Settings, rows: list[dict[str, Any]], locale: str) -> str:
    if settings.gemini_api_key is None:
        raise HTTPException(
            503,
            detail={"code": "AI_UNAVAILABLE", "message": "AI analytics is not configured"},
        )
    language = "Russian" if locale == "ru" else "English"
    prompt = (
        f"Write a concise service-quality summary in {language}. "
        "Identify positive and negative recurring themes and rating changes. "
        "Do not infer protected traits, recommend sanctions, or identify clients. "
        f"Anonymized reviews: {rows}"
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    try:
        response = httpx.post(
            url,
            headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
    except httpx.TimeoutException:
        logger.warning("review_ai_failed category=timeout")
        raise HTTPException(
            504,
            detail={"code": "AI_GEMINI_TIMEOUT", "message": "AI summary timed out"},
        ) from None
    except httpx.RequestError:
        logger.warning("review_ai_failed category=network")
        raise HTTPException(
            503,
            detail={"code": "AI_GEMINI_NETWORK", "message": "AI summary is temporarily unavailable"},
        ) from None
    if response.status_code == 429 or response.status_code >= 500:
        logger.warning("review_ai_failed category=upstream status=%s", response.status_code)
        raise HTTPException(
            503,
            detail={"code": "AI_GEMINI_UNAVAILABLE", "message": "AI summary is temporarily unavailable"},
        )
    if response.status_code >= 400:
        logger.warning("review_ai_failed category=rejected status=%s", response.status_code)
        raise HTTPException(
            502,
            detail={"code": "AI_GEMINI_REJECTED", "message": "AI summary request was rejected"},
        )
    try:
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (ValueError, KeyError, IndexError, AttributeError):
        logger.warning("review_ai_failed category=invalid_response")
        raise HTTPException(
            502,
            detail={"code": "AI_INVALID_RESPONSE", "message": "AI returned an invalid summary"},
        ) from None
    if not text:
        raise HTTPException(
            502,
            detail={"code": "AI_INVALID_RESPONSE", "message": "AI returned an empty summary"},
        )
    return text[:5000]
