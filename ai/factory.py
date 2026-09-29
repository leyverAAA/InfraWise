"""Select an explanation provider without making AI availability a hard dependency."""

from __future__ import annotations

import logging
import os

from .base import AIExplainer
from .ollama_provider import OllamaExplainer
from .template_provider import TemplateExplainer

logger = logging.getLogger(__name__)


def get_explainer() -> AIExplainer:
    """Return the configured provider, falling back to deterministic templates."""
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower() or "ollama"
    if provider in {"template", "fallback", "local_template"}:
        return TemplateExplainer()
    if provider != "ollama":
        logger.warning("Unknown AI_PROVIDER=%s; using template explanations", provider)
        return TemplateExplainer()

    explainer = OllamaExplainer()
    if not explainer.healthcheck():
        logger.warning("Ollama is unavailable; using template explanations")
        return TemplateExplainer()
    return explainer


__all__ = ["get_explainer"]
