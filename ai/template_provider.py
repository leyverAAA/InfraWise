"""Deterministic, network-free explanation provider."""

from schema.architecture import ArchSpec, Decision


class TemplateExplainer:
    """Produce Spanish explanations without an external model or network."""

    def explain(self, spec: ArchSpec) -> list[Decision]:
        existing_factors = {
            decision.component_id: dict(decision.factors) for decision in spec.decisions
        }
        decisions: list[Decision] = []
        for component in spec.components:
            factors = existing_factors.get(component.id, {})
            if not factors:
                factors = {"cost": f"${component.estimated_monthly_cost_usd:.2f} USD/mes"}
            factor_text = ", ".join(f"{key}={value}" for key, value in factors.items())
            reasoning = (
                f"Se seleccionó {component.display_name} para la categoría "
                f"{component.category}. Cumple las restricciones evaluadas por el "
                f"Rule Engine y mantiene un costo estimado de "
                f"${component.estimated_monthly_cost_usd:.2f} USD/mes. "
                f"Factores considerados: {factor_text}."
            )
            decisions.append(
                Decision(
                    component_id=component.id,
                    reasoning=reasoning,
                    factors=factors,
                )
            )
        return decisions


TemplateProvider = TemplateExplainer

__all__ = ["TemplateExplainer", "TemplateProvider"]
