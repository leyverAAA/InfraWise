import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai.base import AIProviderUnavailable
from api.db import Base, get_db
from api.main import app

EXAMPLES = Path(__file__).parents[1] / "examples"
REQUIREMENTS = json.loads((EXAMPLES / "requirements.example.json").read_text(encoding="utf-8"))


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "template")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_post_architecture_persists_and_returns_archspec(client):
    response = client.post("/architectures", json=REQUIREMENTS)

    assert response.status_code == 201
    body = response.json()
    assert body["components"]
    assert len(body["decisions"]) == len(body["components"])
    assert body["total_monthly_cost_usd"] <= REQUIREMENTS["monthly_budget_usd"]

    fetched = client.get(f"/architectures/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["components"] == body["components"]


def test_post_budget_error_is_actionable_422(client):
    payload = {**REQUIREMENTS, "monthly_budget_usd": 1}

    response = client.post("/architectures", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "presupuesto" in response.json()["detail"]


def test_pydantic_validation_returns_422(client):
    payload = {**REQUIREMENTS, "monthly_active_users": 0}

    response = client.post("/architectures", json=payload)

    assert response.status_code == 422


def test_get_missing_architecture_returns_404(client):
    response = client.get("/architectures/does-not-exist")

    assert response.status_code == 404


def test_diagram_endpoint_returns_plain_mermaid(client):
    created = client.post("/architectures", json=REQUIREMENTS).json()

    response = client.get(f"/architectures/{created['id']}/diagram")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.startswith("graph TD")
    assert "api-1" in response.text


def test_provider_failure_falls_back_without_failing_request(client, monkeypatch):
    class FailingExplainer:
        def explain(self, _spec):
            raise AIProviderUnavailable("Ollama unavailable")

    monkeypatch.setattr("api.main.get_explainer", lambda: FailingExplainer())

    response = client.post("/architectures", json=REQUIREMENTS)

    assert response.status_code == 201
    assert response.json()["decisions"]


def test_cors_allows_configured_frontend_origin(client):
    response = client.options(
        "/architectures",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_missing_architecture_diagram_returns_404(client):
    response = client.get("/architectures/missing/diagram")

    assert response.status_code == 404
