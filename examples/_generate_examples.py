"""
Builds the three example JSON files by hand, using only the stdlib
(so it runs without pydantic installed), then asserts the numbers are
internally consistent before writing anything to disk. This is NOT part
of the app — it's just how these example fixtures were produced.
"""

import json
from pathlib import Path

OUT = Path(__file__).parent
EXAMPLE_CREATED_AT = "2026-09-28T00:00:00+00:00"

# ---------------------------------------------------------------------------
# 1. catalog.aws.sample.json — a hand-curated slice of the AWS catalog.
#    Instance-hour prices are 2026 on-demand list prices (us-east-1),
#    converted to a monthly estimate at 730 hours/month.
# ---------------------------------------------------------------------------
HOURS_PER_MONTH = 730

catalog = [
    {
        "id": "aws.ec2.t3.micro",
        "provider": "aws",
        "category": "compute",
        "display_name": "EC2 t3.micro",
        "pricing_model": "instance_hour",
        "base_monthly_usd": round(0.0104 * HOURS_PER_MONTH, 2),
        "unit_price_usd": None,
        "max_rpm": 500,
        "max_users": 1000,
        "min_availability": "standard",
        "notes": "Fine for a dev/staging API. Undersized past ~1k users.",
    },
    {
        "id": "aws.ec2.t3.small",
        "provider": "aws",
        "category": "compute",
        "display_name": "EC2 t3.small",
        "pricing_model": "instance_hour",
        "base_monthly_usd": round(0.0208 * HOURS_PER_MONTH, 2),
        "unit_price_usd": None,
        "max_rpm": 1500,
        "max_users": 5000,
        "min_availability": "standard",
        "notes": "Sweet spot for small/medium APIs on a tight budget.",
    },
    {
        "id": "aws.ec2.t3.medium",
        "provider": "aws",
        "category": "compute",
        "display_name": "EC2 t3.medium",
        "pricing_model": "instance_hour",
        "base_monthly_usd": round(0.0416 * HOURS_PER_MONTH, 2),
        "unit_price_usd": None,
        "max_rpm": 4000,
        "max_users": 15000,
        "min_availability": "standard",
        "notes": "Step up once t3.small saturates on CPU, not just RPM.",
    },
    {
        "id": "aws.rds.postgres.t3.micro",
        "provider": "aws",
        "category": "database",
        "display_name": "RDS PostgreSQL db.t3.micro (single-AZ)",
        "pricing_model": "flat_monthly",
        "base_monthly_usd": 15.0,
        "unit_price_usd": None,
        "max_rpm": 800,
        "max_users": 2000,
        "min_availability": "standard",
        "notes": "No failover. Fine for STANDARD tier only.",
    },
    {
        "id": "aws.rds.postgres.t3.small",
        "provider": "aws",
        "category": "database",
        "display_name": "RDS PostgreSQL db.t3.small (single-AZ)",
        "pricing_model": "flat_monthly",
        "base_monthly_usd": 30.0,
        "unit_price_usd": None,
        "max_rpm": 2000,
        "max_users": 8000,
        "min_availability": "standard",
        "notes": "No failover. Fine for STANDARD tier only.",
    },
    {
        "id": "aws.rds.postgres.t3.small.multiaz",
        "provider": "aws",
        "category": "database",
        "display_name": "RDS PostgreSQL db.t3.small (Multi-AZ)",
        "pricing_model": "flat_monthly",
        "base_monthly_usd": 60.0,
        "unit_price_usd": None,
        "max_rpm": 2000,
        "max_users": 8000,
        "min_availability": "high",
        "notes": "Automatic failover. Required once availability=HIGH or above.",
    },
    {
        "id": "aws.rds.postgres.t3.medium.multiaz",
        "provider": "aws",
        "category": "database",
        "display_name": "RDS PostgreSQL db.t3.medium (Multi-AZ)",
        "pricing_model": "flat_monthly",
        "base_monthly_usd": 120.0,
        "unit_price_usd": None,
        "max_rpm": 5000,
        "max_users": 20000,
        "min_availability": "high",
        "notes": "Multi-AZ + more headroom for medium-scale write traffic.",
    },
    {
        "id": "aws.s3.standard",
        "provider": "aws",
        "category": "storage",
        "display_name": "S3 Standard",
        "pricing_model": "per_unit",
        "base_monthly_usd": 0.0,
        "unit_price_usd": 0.023,
        "max_rpm": None,
        "max_users": None,
        "min_availability": "standard",
        "notes": "$/GB-month. Requests billed separately (ignored in v1 estimate).",
    },
    {
        "id": "aws.alb",
        "provider": "aws",
        "category": "load_balancer",
        "display_name": "Application Load Balancer",
        "pricing_model": "flat_monthly",
        "base_monthly_usd": 16.0,
        "unit_price_usd": None,
        "max_rpm": None,
        "max_users": None,
        "min_availability": "high",
        "notes": "Flat estimate; LCU-based usage cost ignored in v1.",
    },
    {
        "id": "aws.elasticache.redis.t3.micro",
        "provider": "aws",
        "category": "cache",
        "display_name": "ElastiCache Redis t3.micro",
        "pricing_model": "instance_hour",
        "base_monthly_usd": round(0.017 * HOURS_PER_MONTH, 2),
        "unit_price_usd": None,
        "max_rpm": None,
        "max_users": None,
        "min_availability": "standard",
        "notes": "Optional — only pulled in when optimize_for=performance.",
    },
    {
        "id": "aws.cloudfront",
        "provider": "aws",
        "category": "cdn",
        "display_name": "CloudFront",
        "pricing_model": "per_unit",
        "base_monthly_usd": 0.0,
        "unit_price_usd": 0.085,
        "max_rpm": None,
        "max_users": None,
        "min_availability": "standard",
        "notes": "$/GB transferred out. Only added for STATIC_SITE / high-traffic tiers.",
    },
]

# ---------------------------------------------------------------------------
# 2. requirements.example.json — the input from the write-up's own example.
# ---------------------------------------------------------------------------
requirements = {
    "app_type": "web_api",
    "monthly_active_users": 5000,
    "requests_per_minute": 300,
    "database": "postgresql",
    "storage_gb": 50,
    "availability": "high",
    "monthly_budget_usd": 150,
    "region": "us-east-1",
    "optimize_for": "balanced",
}

# ---------------------------------------------------------------------------
# 3. architecture.example.json — what the Rule Engine *would* produce for
#    the requirements above, picked by hand here so the fixture is legible,
#    but constrained to only use catalog entries defined above.
# ---------------------------------------------------------------------------
by_id = {c["id"]: c for c in catalog}


def cost_of(service_id: str, count: int = 1, size_gb: float | None = None) -> float:
    svc = by_id[service_id]
    if svc["pricing_model"] == "per_unit":
        return round(svc["unit_price_usd"] * (size_gb or 0), 2)
    return round(svc["base_monthly_usd"] * count, 2)


components = [
    {
        "id": "lb-1",
        "service_id": "aws.alb",
        "category": "load_balancer",
        "display_name": by_id["aws.alb"]["display_name"],
        "count": 1,
        "config": {},
        "estimated_monthly_cost_usd": cost_of("aws.alb"),
    },
    {
        "id": "api-1",
        "service_id": "aws.ec2.t3.small",
        "category": "compute",
        "display_name": by_id["aws.ec2.t3.small"]["display_name"],
        "count": 2,
        "config": {"multi_az": True},
        "estimated_monthly_cost_usd": cost_of("aws.ec2.t3.small", count=2),
    },
    {
        "id": "db-1",
        "service_id": "aws.rds.postgres.t3.small.multiaz",
        "category": "database",
        "display_name": by_id["aws.rds.postgres.t3.small.multiaz"]["display_name"],
        "count": 1,
        "config": {"engine": "postgresql", "multi_az": True},
        "estimated_monthly_cost_usd": cost_of("aws.rds.postgres.t3.small.multiaz"),
    },
    {
        "id": "storage-1",
        "service_id": "aws.s3.standard",
        "category": "storage",
        "display_name": by_id["aws.s3.standard"]["display_name"],
        "count": 1,
        "config": {"size_gb": 50},
        "estimated_monthly_cost_usd": cost_of("aws.s3.standard", size_gb=50),
    },
]

connections = [
    {"source": "lb-1", "target": "api-1", "label": "HTTP"},
    {"source": "api-1", "target": "db-1", "label": "reads/writes"},
    {"source": "api-1", "target": "storage-1", "label": "reads/writes"},
]

decisions = [
    {
        "component_id": "api-1",
        "reasoning": (
            "Two t3.small instances behind the load balancer, instead of one bigger "
            "instance, because availability=HIGH rules out a single point of failure "
            "and 300 req/min fits well within two t3.small's combined ~3,000 rpm ceiling."
        ),
        "factors": {"cost": "medium", "scalability": "high", "availability": "high"},
    },
    {
        "component_id": "db-1",
        "reasoning": (
            "Multi-AZ PostgreSQL is required (not optional) once availability=HIGH is "
            "set — it's the only DB option in the catalog whose min_availability is "
            "'high'. db.t3.small was chosen over db.t3.medium because 5,000 users / "
            "300 rpm sits well under its capacity ceiling, saving $60/month."
        ),
        "factors": {"cost": "medium", "scalability": "medium", "availability": "high"},
    },
    {
        "component_id": "storage-1",
        "reasoning": (
            "S3 Standard for 50GB of object storage — no cheaper tier fits the "
            "access pattern of an active API."
        ),
        "factors": {"cost": "low", "operational_overhead": "low"},
    },
]

total_cost = round(sum(c["estimated_monthly_cost_usd"] for c in components), 2)

architecture = {
    "id": "archspec-2026-09-28-001",
    "provider": "aws",
    "requirements": requirements,
    "components": components,
    "connections": connections,
    "decisions": decisions,
    "score": {
        "cost_usd_month": total_cost,
        "complexity": "medium",
        "scalability": "high",
        "availability_pct": 99.9,
        "operational_overhead": "medium",
    },
    "total_monthly_cost_usd": total_cost,
    "created_at": EXAMPLE_CREATED_AT,
}

# ---------------------------------------------------------------------------
# Sanity checks — these are exactly the kind of assertions the real
# Cost Engine and Rule Engine tests should encode.
# ---------------------------------------------------------------------------
assert total_cost < requirements["monthly_budget_usd"], "Example exceeds its own budget!"
assert by_id["aws.rds.postgres.t3.small.multiaz"]["min_availability"] == "high"
component_ids = {c["id"] for c in components}
for conn in connections:
    assert conn["source"] in component_ids and conn["target"] in component_ids
print(f"OK — total_monthly_cost_usd={total_cost} (budget={requirements['monthly_budget_usd']})")

# ---------------------------------------------------------------------------
# Write files
#
# encoding is pinned to utf-8 explicitly: without it, write_text() uses the
# platform locale, which on Windows writes cp1252 and turns the em-dashes
# above into single bytes. The tests read these fixtures back with
# encoding="utf-8", so a locale-default write silently breaks the suite.
# ---------------------------------------------------------------------------
for name, payload in (
    ("catalog.aws.sample.json", catalog),
    ("requirements.example.json", requirements),
    ("architecture.example.json", architecture),
):
    (OUT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
print("Wrote catalog.aws.sample.json, requirements.example.json, architecture.example.json")
