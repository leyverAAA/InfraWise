"""Typed catalog entries consumed by the deterministic rule and cost engines."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentCategory(StrEnum):
    COMPUTE = "compute"
    DATABASE = "database"
    STORAGE = "storage"
    LOAD_BALANCER = "load_balancer"
    CACHE = "cache"
    CDN = "cdn"


class PricingModel(StrEnum):
    FLAT_MONTHLY = "flat_monthly"
    INSTANCE_HOUR = "instance_hour"
    PER_UNIT = "per_unit"


class CatalogService(BaseModel):
    """A normalized, provider-specific service option.

    Prices in ``base_monthly_usd`` are already monthly estimates. Keeping that
    contract in the model prevents the rule engine from silently mixing hourly
    and monthly values.
    """

    id: str
    provider: str
    category: ComponentCategory
    display_name: str
    pricing_model: PricingModel
    base_monthly_usd: float = Field(ge=0)
    unit_price_usd: float | None = Field(default=None, ge=0)
    max_rpm: int | None = Field(default=None, gt=0)
    max_users: int | None = Field(default=None, gt=0)
    min_availability: str
    notes: str = ""

    model_config = {"use_enum_values": True}
