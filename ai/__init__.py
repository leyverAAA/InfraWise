"""AI explanation providers and their stable public contract."""

from .base import AIExplainer, AIProviderUnavailable
from .factory import get_explainer
from .ollama_provider import OllamaExplainer, OllamaProvider
from .template_provider import TemplateExplainer, TemplateProvider

__all__ = [
    "AIExplainer",
    "AIProviderUnavailable",
    "OllamaExplainer",
    "OllamaProvider",
    "TemplateExplainer",
    "TemplateProvider",
    "get_explainer",
]
