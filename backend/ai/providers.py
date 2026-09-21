"""AI provider abstraction — optional enhancement, never the foundation.

All providers return plain dicts; every value is validated against the same
enums the rule engine uses. Anything invalid is discarded (caller falls back
to deterministic rules). No API keys in code — environment only.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

VALID_CLAUSE_TYPES = {
    "DEFINITIONS", "PAYMENT", "RENEWAL", "TERMINATION", "INSURANCE",
    "CONFIDENTIALITY", "SECURITY", "COMPLIANCE", "SLA", "REPORTING",
    "AUDIT", "LIABILITY", "INDEMNIFICATION", "NOTICE", "DELIVERY", "GENERAL",
}


def clamp_confidence(value) -> float:
    try:
        return max(0.0, min(0.95, float(value)))
    except (TypeError, ValueError):
        return 0.5


def validated_classification(raw: dict | None) -> dict | None:
    """Accept {clause_type, confidence}; reject anything else (→ None)."""
    if not isinstance(raw, dict):
        return None
    clause_type = str(raw.get("clause_type", "")).upper()
    if clause_type not in VALID_CLAUSE_TYPES:
        return None
    return {"clause_type": clause_type, "confidence": clamp_confidence(raw.get("confidence", 0.5))}


def extract_json_object(text: str) -> dict | None:
    """Pull the first JSON object from model output (fences tolerated)."""
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = match.group(1) if match else text[text.find("{"): text.rfind("}") + 1]
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str
    timeout: int


class BaseProvider:
    name = "none"

    def __init__(self, config: ProviderConfig):
        self.config = config

    def classify_clause(self, text: str) -> dict | None:
        raise NotImplementedError


def _post_json(url: str, payload: dict, api_key: str, timeout: int,
               headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


class OpenAICompatibleProvider(BaseProvider):
    """Works with OpenAI and any OpenAI-compatible endpoint (custom base URL)."""
    name = "openai"

    def classify_clause(self, text: str) -> dict | None:
        payload = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": (
                    "Classify the contract clause into exactly one of: "
                    + ", ".join(sorted(VALID_CLAUSE_TYPES))
                    + ". Reply with JSON only: {\"clause_type\": \"...\", \"confidence\": 0.0-0.95}."
                )},
                {"role": "user", "content": text[:4000]},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        raw = _post_json(f"{self.config.base_url.rstrip('/')}/chat/completions",
                         payload, self.config.api_key, self.config.timeout)
        content = raw["choices"][0]["message"]["content"]
        return validated_classification(extract_json_object(content))


class GeminiProvider(BaseProvider):
    name = "gemini"

    def classify_clause(self, text: str) -> dict | None:
        payload = {
            "contents": [{"parts": [{"text": (
                "Classify the contract clause into exactly one of: "
                + ", ".join(sorted(VALID_CLAUSE_TYPES))
                + ". Reply with JSON only: {\"clause_type\": \"...\", \"confidence\": 0.0-0.95}.\n\n"
                + text[:4000]
            )}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.config.model or 'gemini-2.0-flash'}:generateContent?key={self.config.api_key}")
        raw = _post_json(url, payload, self.config.api_key, self.config.timeout,
                         headers={"x-goog-api-key": self.config.api_key})
        content = raw["candidates"][0]["content"]["parts"][0]["text"]
        return validated_classification(extract_json_object(content))
