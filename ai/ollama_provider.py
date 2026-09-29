"""Ollama-backed explanation provider with strict contract validation."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from schema.architecture import ArchSpec, Decision

from .base import AIProviderUnavailable

SYSTEM_PROMPT = (
    "Eres un explicador de arquitecturas Cloud. Devuelve únicamente JSON con la "
    'forma {"decisions":[{"component_id":"...","reasoning":"..."}]}. '
    "Explica cada componente usando SOLO los componentes y factores recibidos. "
    "No sugieras, inventes ni menciones servicios que no estén en la lista. "
    "No cambies componentes, conexiones, costos ni cantidades. Escribe en español."
)


class OllamaExplainer:
    """Call Ollama locally and keep the model outside the domain boundary."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout if timeout is not None else self._configured_timeout()

    @staticmethod
    def _configured_timeout() -> float:
        try:
            return max(3.0, min(float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "4")), 5.0))
        except ValueError:
            return 4.0

    def healthcheck(self) -> bool:
        """Return whether Ollama responds quickly enough to be selected."""
        try:
            req = request.Request(f"{self.base_url}/api/tags", method="GET")
            with request.urlopen(req, timeout=min(self.timeout, 1.0)) as response:
                return 200 <= getattr(response, "status", 200) < 300
        except (error.URLError, TimeoutError, OSError):
            return False

    def explain(self, spec: ArchSpec) -> list[Decision]:
        payload = self._chat_payload(spec)
        try:
            response = self._post_json(f"{self.base_url}/api/chat", payload)
            return self._parse_decisions(response, spec)
        except AIProviderUnavailable:
            raise
        except (
            error.URLError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ) as exc:
            raise AIProviderUnavailable(f"Ollama explanation failed: {exc}") from exc

    def _chat_payload(self, spec: ArchSpec) -> dict[str, Any]:
        factors = {decision.component_id: decision.factors for decision in spec.decisions}
        context = {
            "components": [
                {
                    "id": component.id,
                    "service_id": component.service_id,
                    "category": component.category,
                    "display_name": component.display_name,
                    "count": component.count,
                    "estimated_monthly_cost_usd": component.estimated_monthly_cost_usd,
                    "factors": factors.get(component.id, {}),
                }
                for component in spec.components
            ]
        }
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, sort_keys=True),
                },
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise AIProviderUnavailable(f"Ollama request unavailable: {exc}") from exc

    @staticmethod
    def _parse_decisions(response: dict[str, Any], spec: ArchSpec) -> list[Decision]:
        try:
            content = response["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty Ollama content")
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(cleaned)
            items = parsed["decisions"] if isinstance(parsed, dict) else parsed
            if not isinstance(items, list):
                raise ValueError("decisions must be a list")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderUnavailable(f"Ollama returned invalid decisions: {exc}") from exc

        expected_ids = [component.id for component in spec.components]
        received_ids = [item.get("component_id") for item in items if isinstance(item, dict)]
        if len(items) != len(expected_ids) or received_ids != expected_ids:
            raise AIProviderUnavailable(
                "Ollama decisions must contain exactly one entry per component in order"
            )

        original_factors = {decision.component_id: decision.factors for decision in spec.decisions}
        decisions: list[Decision] = []
        for item in items:
            reasoning = item.get("reasoning")
            if not isinstance(reasoning, str) or not reasoning.strip():
                raise AIProviderUnavailable("Ollama returned an empty component reasoning")
            decisions.append(
                Decision(
                    component_id=item["component_id"],
                    reasoning=reasoning.strip(),
                    factors=original_factors.get(item["component_id"], {}),
                )
            )
        return decisions


OllamaProvider = OllamaExplainer

__all__ = ["OllamaExplainer", "OllamaProvider", "SYSTEM_PROMPT"]
