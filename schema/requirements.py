"""
Requirements: the structured input to the Rule Engine.

This is what a user's plain-language request —
"API for 5,000 users, Postgres, high availability, $150/month budget"—
gets normalized into. Either a form fills this directly, or the AI layer
parses free text into this shape later; either way, everything downstream
only ever sees a Requirements object.

Deliberately provider-agnostic: nothing here mentions AWS, EC2, or RDS.
That mapping is the Rule Engine's job (see catalog.py + architecture.py).
Keeping that boundary is what makes "add GCP later" additive instead of
a rewrite.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class AppType(StrEnum):
    WEB_API = "web_api"
    WEB_APP = "web_app"
    STATIC_SITE = "static_site"
    BACKGROUND_WORKER = "background_worker"


class DatabaseEngine(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    NONE = "none"


class AvailabilityTier(StrEnum):
    """A hard constraint the Rule Engine filters the catalog against —
    not a nice-to-have. E.g. CRITICAL rules out any single-AZ service."""

    STANDARD = "standard"  # ~99.5% — single instance, daily backups
    HIGH = "high"  # ~99.9% — multi-AZ, load balanced
    CRITICAL = "critical"  # ~99.99% — multi-AZ + read replicas


class OptimizeFor(StrEnum):
    COST = "cost"
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    SIMPLICITY = "simplicity"
    BALANCED = "balanced"


class Requirements(BaseModel):
    app_type: AppType
    monthly_active_users: int = Field(gt=0)
    requests_per_minute: int = Field(gt=0)
    database: DatabaseEngine = DatabaseEngine.POSTGRESQL
    storage_gb: float = Field(ge=0)
    availability: AvailabilityTier = AvailabilityTier.STANDARD
    monthly_budget_usd: float = Field(gt=0)
    region: str = "us-east-1"
    optimize_for: OptimizeFor = OptimizeFor.BALANCED

    model_config = {"use_enum_values": True}
