"""Phase 14 tests — AI optional, validated, never fatal."""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from ai.providers import clamp_confidence, extract_json_object, validated_classification
from ai.service import classify_clause_ai, get_provider, status

User = get_user_model()


def test_no_provider_by_default():
    assert get_provider() is None
    assert classify_clause_ai("The Vendor shall maintain insurance.") is None
    assert status()["configured"] is False


@override_settings(AI_PROVIDER="openai", OPENAI_API_KEY="")
def test_missing_key_means_unconfigured():
    assert get_provider() is None


@override_settings(AI_PROVIDER="openai", OPENAI_API_KEY="test-key", OPENAI_BASE_URL="http://localhost:9", AI_TIMEOUT_SECONDS=1)
def test_provider_errors_fall_back_to_none():
    # Unreachable endpoint → None, never raises.
    assert classify_clause_ai("The Vendor shall maintain insurance.") is None


def test_validation_rejects_garbage():
    assert validated_classification(None) is None
    assert validated_classification({"clause_type": "NOPE", "confidence": 0.9}) is None
    assert validated_classification({"confidence": 0.9}) is None
    ok = validated_classification({"clause_type": "insurance", "confidence": 99})
    assert ok == {"clause_type": "INSURANCE", "confidence": 0.95}
    assert clamp_confidence("junk") == 0.5


def test_json_extraction_tolerates_fences():
    assert extract_json_object('```json\n{"clause_type": "PAYMENT", "confidence": 0.8}\n```') == {
        "clause_type": "PAYMENT", "confidence": 0.8}
    assert extract_json_object("not json") is None


@pytest.mark.django_db
def test_status_and_classify_endpoints():
    user = User.objects.create_user(email="ai@example.com", password="password123")
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.get("/api/v1/ai/status/").json()["configured"] is False
    r = client.post("/api/v1/ai/classify/", {"text": "The Vendor shall maintain insurance."}, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["used"] == "RULE" and body["rule"]["clause_type"] == "INSURANCE" and body["ai"] is None
    assert client.post("/api/v1/ai/classify/", {"text": "short"}, format="json").status_code == 400
