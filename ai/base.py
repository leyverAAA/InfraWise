"""Provider-neutral AI explanation contract for architecture decisions."""

from typing import Protocol

from schema.architecture import ArchSpec, Decision


class AIProviderUnavailable(RuntimeError):
    """The configured explanation provider cannot return a valid response."""


class AIExplainer(Protocol):
    """Stable boundary for explanation providers.

    This interface is intentional: adding OpenAI or Gemini later should mean
    adding a provider class, not rewriting the API or the architecture engine.
    Providers may rewrite only ``Decision.reasoning``; components and
    connections are owned by the deterministic Rule Engine.
    """

    def explain(self, spec: ArchSpec) -> list[Decision]:
        """Return exactly one explanation decision for every component."""
        ...
