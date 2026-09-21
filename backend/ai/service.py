"""AI service facade — returns None whenever AI is unavailable or unusable.

Callers treat None as 'use deterministic rules'. This function never raises
for provider failures (network, auth, malformed output).
"""
from __future__ import annotations

from django.conf import settings

from .providers import (
    BaseProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
    ProviderConfig,
    validated_classification,
)


def get_provider() -> BaseProvider | None:
    provider = (getattr(settings, "AI_PROVIDER", "none") or "none").lower()
    timeout = int(getattr(settings, "AI_TIMEOUT_SECONDS", 30))
    if provider == "openai":
        key = getattr(settings, "OPENAI_API_KEY", "")
        if not key:
            return None
        return OpenAICompatibleProvider(ProviderConfig(
            name="openai", api_key=key,
            model=getattr(settings, "AI_MODEL", "") or "gpt-4o-mini",
            base_url=getattr(settings, "OPENAI_BASE_URL", "") or "https://api.openai.com/v1",
            timeout=timeout,
        ))
    if provider == "gemini":
        key = getattr(settings, "GEMINI_API_KEY", "")
        if not key:
            return None
        return GeminiProvider(ProviderConfig(
            name="gemini", api_key=key,
            model=getattr(settings, "AI_MODEL", "") or "gemini-2.0-flash",
            base_url="", timeout=timeout,
        ))
    return None


def status() -> dict:
    provider = get_provider()
    configured_name = (getattr(settings, "AI_PROVIDER", "none") or "none").lower()
    if provider is None:
        return {"provider": configured_name, "configured": False,
                "model": getattr(settings, "AI_MODEL", "") or None,
                "note": "AI unavailable — deterministic engines serve all requests."}
    return {"provider": provider.name, "configured": True,
            "model": provider.config.model, "note": "AI enhances classification; rules remain the fallback."}


def classify_clause_ai(text: str) -> dict | None:
    """AI clause classification, validated. None → use rule engine."""
    provider = get_provider()
    if provider is None:
        return None
    try:
        return validated_classification(provider.classify_clause(text))
    except Exception:  # never break the pipeline on AI failure
        return None
