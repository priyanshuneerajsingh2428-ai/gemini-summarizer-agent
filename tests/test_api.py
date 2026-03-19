"""
tests/test_api.py — Unit tests for the FastAPI endpoints.

Run locally:
    pip install pytest httpx
    pytest tests/ -v
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

MOCK_JSON_RESPONSE = json.dumps({
    "summary": "AI is transforming industries with broad implications for safety and ethics.",
    "word_count": 85,
    "key_topics": ["artificial intelligence", "safety", "ethics", "machine learning"],
    "sentiment": "neutral",
})

SAMPLE_TEXT = (
    "Artificial intelligence is transforming industries at an unprecedented pace. "
    "From healthcare diagnostics to autonomous vehicles, machine learning models are "
    "being embedded into critical systems. Researchers and policymakers are racing to "
    "establish frameworks that ensure AI systems are fair, explainable, and aligned "
    "with human values."
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["agent"] == "summarizer_agent"
    assert data["model"] == "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Agent card
# ---------------------------------------------------------------------------
def test_agent_card():
    response = client.get("/agent-card")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "summarizer_agent"
    assert "text-summarization" in data["capabilities"]
    assert "/summarize" in data["endpoint"]


# ---------------------------------------------------------------------------
# Summarize — happy path (mocked ADK runner)
# ---------------------------------------------------------------------------
@patch("main.run_agent", new_callable=AsyncMock, return_value=MOCK_JSON_RESPONSE)
def test_summarize_bullet(mock_runner):
    response = client.post(
        "/summarize",
        json={"text": SAMPLE_TEXT, "style": "bullet"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] != ""
    assert data["word_count"] > 0
    assert isinstance(data["key_topics"], list)
    assert data["sentiment"] in ("positive", "neutral", "negative")
    assert data["style"] == "bullet"
    assert data["model"] == "gemini-2.0-flash"


@patch("main.run_agent", new_callable=AsyncMock, return_value=MOCK_JSON_RESPONSE)
def test_summarize_paragraph(mock_runner):
    response = client.post(
        "/summarize",
        json={"text": SAMPLE_TEXT, "style": "paragraph"},
    )
    assert response.status_code == 200
    assert response.json()["style"] == "paragraph"


# ---------------------------------------------------------------------------
# Summarize — validation errors
# ---------------------------------------------------------------------------
def test_summarize_empty_text():
    response = client.post(
        "/summarize",
        json={"text": "", "style": "bullet"},
    )
    assert response.status_code == 422  # Pydantic min_length validation


def test_summarize_invalid_style():
    response = client.post(
        "/summarize",
        json={"text": SAMPLE_TEXT, "style": "emoji"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Summarize — graceful JSON fallback
# ---------------------------------------------------------------------------
@patch("main.run_agent", new_callable=AsyncMock, return_value="This is a plain text summary without JSON.")
def test_summarize_non_json_fallback(mock_runner):
    response = client.post(
        "/summarize",
        json={"text": SAMPLE_TEXT, "style": "bullet"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "plain text" in data["summary"]
    assert data["key_topics"] == []
    assert data["sentiment"] == "neutral"
