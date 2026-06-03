"""Tests for the FastAPI web layer (offline, stub provider)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_home_roadmap(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "divorce roadmap" in r.text.lower()
    assert "Legal information, not legal advice" in r.text


def test_step_detail_partial(client):
    r = client.get("/step/serve_respondent")
    assert r.status_code == 200
    assert "Divorce Summons" in r.text
    assert "Must contain" in r.text


def test_step_detail_unknown(client):
    r = client.get("/step/does_not_exist")
    assert r.status_code == 404


def test_ask_page(client):
    r = client.get("/ask")
    assert r.status_code == 200
    assert "grounded" in r.text.lower()


def test_ask_grounded(client):
    r = client.post("/ask", data={"question": "What is the residency requirement to file?"})
    assert r.status_code == 200
    assert "Grounded answer" in r.text
    assert "pp-cite" in r.text  # inline citation chip
    assert "Confidence" in r.text


def test_ask_advice_refusal(client):
    r = client.post("/ask", data={"question": "Should I file for divorce?"})
    assert r.status_code == 200
    assert "can't give legal advice" in r.text
    assert "Get real legal help" in r.text


def test_ask_out_of_scope(client):
    r = client.post("/ask", data={"question": "How do I file in California?"})
    assert r.status_code == 200
    assert "scope" in r.text.lower()


def test_api_ask_json(client):
    r = client.get("/api/ask", params={"q": "Can I appear by Zoom?"})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "grounded"
    assert data["citations"]
    assert data["is_legal_information"] is True
    assert data["disclaimer"]


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["provider"] == "stub"
    assert data["corpus"]["chunks"] > 0


def test_about_verify_table(client):
    r = client.get("/about")
    assert r.status_code == 200
    assert "Pending verification" in r.text


def test_matter_progress_roundtrip(client):
    created = client.post("/matter", data={"label": "Test matter"})
    assert created.status_code == 200
    mid = created.json()["id"]

    toggled = client.post(
        "/matter/%d/step/serve_respondent" % mid, data={"done": "true"}
    )
    assert toggled.status_code == 200
    assert "Done" in toggled.text
