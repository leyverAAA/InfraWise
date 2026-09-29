import json
import random
from pathlib import Path

import pytest

from engine.rule_engine import NoViableArchitecture, filter_catalog, pick_cheapest, recommend
from schema.catalog import CatalogService, ComponentCategory
from schema.requirements import (
    AppType,
    AvailabilityTier,
    DatabaseEngine,
    OptimizeFor,
    Requirements,
)

EXAMPLES = Path(__file__).parents[1] / "examples"


def load_catalog() -> list[CatalogService]:
    return [
        CatalogService.model_validate(item)
        for item in json.loads((EXAMPLES / "catalog.aws.sample.json").read_text(encoding="utf-8"))
    ]


def load_requirements() -> Requirements:
    return Requirements.model_validate(
        json.loads((EXAMPLES / "requirements.example.json").read_text(encoding="utf-8"))
    )


def test_matches_example_fixture():
    spec = recommend(load_requirements(), load_catalog())
    expected = json.loads((EXAMPLES / "architecture.example.json").read_text(encoding="utf-8"))

    actual_components = sorted(
        (component.service_id, component.category, component.count) for component in spec.components
    )
    expected_components = sorted(
        (component["service_id"], component["category"], component["count"])
        for component in expected["components"]
    )

    assert actual_components == expected_components
    assert spec.total_monthly_cost_usd <= load_requirements().monthly_budget_usd


def test_filter_catalog_applies_provider_category_capacity_and_availability():
    req = load_requirements()
    candidates = filter_catalog(load_catalog(), ComponentCategory.COMPUTE, req)

    assert [candidate.id for candidate in candidates] == [
        "aws.ec2.t3.small",
        "aws.ec2.t3.medium",
    ]


def test_pick_cheapest_returns_lowest_monthly_option():
    candidates = filter_catalog(load_catalog(), ComponentCategory.DATABASE, load_requirements())
    assert pick_cheapest(candidates).id == "aws.rds.postgres.t3.small.multiaz"


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (ComponentCategory.COMPUTE, True),
        (ComponentCategory.DATABASE, True),
        (ComponentCategory.STORAGE, True),
        (ComponentCategory.LOAD_BALANCER, True),
        (ComponentCategory.CACHE, False),
        (ComponentCategory.CDN, False),
    ],
)
def test_phase_one_category_rules(category, expected):
    spec = recommend(load_requirements(), load_catalog())
    assert any(component.category == category.value for component in spec.components) is expected


def test_performance_adds_cache_and_static_site_adds_cdn():
    req = load_requirements().model_copy(
        update={"optimize_for": OptimizeFor.PERFORMANCE, "app_type": AppType.STATIC_SITE}
    )
    spec = recommend(req, load_catalog())
    categories = {component.category for component in spec.components}
    assert "cache" in categories
    assert "cdn" in categories


def test_connections_follow_present_categories():
    spec = recommend(load_requirements(), load_catalog())
    connections = {(item.source, item.target, item.label) for item in spec.connections}
    assert ("lb-1", "api-1", "HTTP") in connections
    assert ("api-1", "db-1", "reads/writes") in connections
    assert ("api-1", "storage-1", "reads/writes") in connections


def test_budget_too_low_raises_explanatory_error():
    req = load_requirements().model_copy(update={"monthly_budget_usd": 1})
    with pytest.raises(NoViableArchitecture, match="presupuesto|budget"):
        recommend(req, load_catalog())


def test_critical_availability_reports_catalog_gap():
    req = load_requirements().model_copy(update={"availability": AvailabilityTier.CRITICAL})
    with pytest.raises(NoViableArchitecture, match="catálogo|catalog"):
        recommend(req, load_catalog())


def test_never_exceeds_budget_for_valid_random_inputs():
    rng = random.Random(20260928)
    for _ in range(50):
        req = Requirements(
            app_type=rng.choice(list(AppType)),
            monthly_active_users=rng.randint(1, 15_000),
            requests_per_minute=rng.randint(1, 4_000),
            database=rng.choice([DatabaseEngine.NONE, DatabaseEngine.POSTGRESQL]),
            storage_gb=rng.uniform(0, 100),
            availability=rng.choice([AvailabilityTier.STANDARD, AvailabilityTier.HIGH]),
            monthly_budget_usd=rng.uniform(1, 400),
            optimize_for=rng.choice(list(OptimizeFor)),
        )
        try:
            spec = recommend(req, load_catalog())
        except NoViableArchitecture:
            continue
        assert spec.total_monthly_cost_usd <= req.monthly_budget_usd
