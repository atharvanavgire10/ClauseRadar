"""Phase 00 smoke tests — health, readiness, API envelope."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint():
    client = APIClient()
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_ready_endpoint_reports_database():
    client = APIClient()
    response = client.get("/api/ready/")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["checks"]["database"] == "ok"


def test_api_info_endpoint():
    client = APIClient()
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json()["name"] == "ClauseRadar API"
