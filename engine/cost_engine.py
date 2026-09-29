"""Cost calculations for catalog services.

The function intentionally has no I/O or provider SDK dependency, which makes
pricing assumptions easy to test and keeps CI deterministic.
"""

from schema.catalog import CatalogService, PricingModel


class CostCatalogError(ValueError):
    """The catalog entry is incomplete for its declared pricing model."""


def estimate_cost(service: CatalogService, count: int = 1, size_gb: float | None = None) -> float:
    """Return the estimated monthly USD cost for a service selection.

    ``instance_hour`` is already converted to a monthly estimate in the sample
    catalog, so it intentionally follows the same calculation as a flat fee.
    """
    if count <= 0:
        raise ValueError("count must be greater than zero")

    if service.pricing_model == PricingModel.PER_UNIT.value:
        if size_gb is None:
            raise ValueError("size_gb is required for per_unit services")
        if service.unit_price_usd is None:
            raise CostCatalogError(
                f"service {service.id} declares per_unit pricing but unit_price_usd is missing"
            )
        return round(service.unit_price_usd * size_gb * count, 2)

    if service.pricing_model in {
        PricingModel.FLAT_MONTHLY.value,
        PricingModel.INSTANCE_HOUR.value,
    }:
        return round(service.base_monthly_usd * count, 2)

    raise CostCatalogError(
        f"service {service.id} uses unsupported pricing model {service.pricing_model!r}"
    )
