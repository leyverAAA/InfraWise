"""
ArchSpec: the single artifact that flows through the whole system.

    Requirements -> [Rule Engine] -> ArchSpec (components, connections)
                 -> [Cost Engine] -> ArchSpec (+ costs, score)
                 -> [AI layer]    -> ArchSpec (+ decisions)
                 -> [frontend]    -> Mermaid diagram (reads ArchSpec)
                 -> [exporter]    -> Terraform (reads ArchSpec)  # roadmap

Every stage reads an ArchSpec and returns a *new, more complete* ArchSpec.
None of them mutate one in place, and none of them re-derive requirements
or re-pick services from scratch — an ArchSpec is a frozen snapshot,
including a copy of the Requirements that produced it.

That immutability is what makes two things trivial later:
  - "before vs. after optimization" diffs (v1 spec vs v2 spec, same id family)
  - audit history (you can always answer "what did we recommend on March 3rd
    and why", because the old ArchSpec + its Requirements never changed)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from .requirements import Requirements


class Level(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Component(BaseModel):
    id: str  # unique within this ArchSpec: "api-1", "db-1"
    service_id: str  # FK into the catalog: "aws.ec2.t3.small"
    category: str  # denormalized from CatalogService, for convenience
    display_name: str
    count: int = 1
    config: dict = Field(default_factory=dict)  # e.g. {"engine": "postgresql", "multi_az": True}
    estimated_monthly_cost_usd: float = 0.0


class Connection(BaseModel):
    source: str  # Component.id
    target: str  # Component.id
    label: str | None = None  # "HTTP", "reads/writes"


class Decision(BaseModel):
    """One justification, one component. This is what turns 'used EC2'
    into 'chose EC2 because...' — see the product write-up's point 4."""

    component_id: str
    reasoning: str
    factors: dict[str, str] = Field(default_factory=dict)  # {"cost": "...", "scalability": "..."}


class ScoreCard(BaseModel):
    cost_usd_month: float
    complexity: Level
    scalability: Level
    availability_pct: float
    operational_overhead: Level


class ArchSpec(BaseModel):
    id: str
    provider: Literal["aws"] = "aws"
    requirements: Requirements  # snapshot, not a reference
    components: list[Component]
    connections: list[Connection]
    decisions: list[Decision] = Field(default_factory=list)
    score: ScoreCard | None = None
    total_monthly_cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"use_enum_values": True}
