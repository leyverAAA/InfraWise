import json
from pathlib import Path

import pytest

from ai.base import AIProviderUnavailable
from ai.factory import get_explainer
from ai.ollama_provider import OllamaExplainer
from ai.template_provider import TemplateExplainer
from engine.rule_engine import recommend
from schema.architecture import ArchSpec
from schema.catalog import CatalogService
from schema.requirements import Requirements

EXAMPLES = Path(__file__).parents[1] / "examples"


def load_spec() -> ArchSpec:
    requirements = Requirements.model_validate(
        json.loads((EXAMPLES / "requirements.example.json").read_text(encoding="utf-8"))
    )
    catalog = [
        CatalogService.model_validate(item)
        for item in json.loads((EXAMPLES / "catalog.aws.sample.json").read_text(encoding="utf-8"))
    ]
    return recommend(requirements, catalog)


def test_template_provider_returns_one_decision_per_component_in_spanish():
    spec = load_spec()

    decisions = TemplateExplainer().explain(spec)

    assert len(decisions) == len(spec.components)
    assert {decision.component_id for decision in decisions} == {
        component.id for component in spec.components
    }
    assert all(decision.reasoning for decision in decisions)
    assert any(word in decisions[0].reasoning.lower() for word in ("seleccion", "componente"))


def test_factory_uses_template_when_ollama_healthcheck_fails(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(OllamaExplainer, "healthcheck", lambda self: False)

    explainer = get_explainer()

    assert isinstance(explainer, TemplateExplainer)


def test_factory_honors_explicit_template_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "template")

    assert isinstance(get_explainer(), TemplateExplainer)


def test_ollama_prompt_contains_only_architecture_context(monkeypatch):
    spec = load_spec()
    captured = {}
    response = {
        "message": {
            "content": json.dumps(
                {
                    "decisions": [
                        {
                            "component_id": component.id,
                            "reasoning": (
                                f"Se eligió {component.display_name} por los factores declarados."
                            ),
                        }
                        for component in spec.components
                    ]
                }
            )
        }
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(response).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("ai.ollama_provider.request.urlopen", fake_urlopen)
    decisions = OllamaExplainer().explain(spec)

    assert len(decisions) == len(spec.components)
    assert "connections" not in json.dumps(captured["body"])
    assert "requirements" not in json.dumps(captured["body"])
    assert "SOLO" in captured["body"]["messages"][0]["content"]
    assert captured["timeout"] <= 5


def test_ollama_invalid_component_contract_is_unavailable(monkeypatch):
    spec = load_spec()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"message": {"content": '{"decisions": []}'}}).encode()

    monkeypatch.setattr(
        "ai.ollama_provider.request.urlopen", lambda *_args, **_kwargs: FakeResponse()
    )

    with pytest.raises(AIProviderUnavailable, match="decisions|component"):
        OllamaExplainer().explain(spec)
