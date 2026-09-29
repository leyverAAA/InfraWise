"""Deterministic AWS architecture selection rules for Phase 1."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from engine.cost_engine import estimate_cost
from schema.architecture import ArchSpec, Component, Connection, Decision, Level, ScoreCard
from schema.catalog import CatalogService, ComponentCategory, PricingModel
from schema.requirements import AvailabilityTier, DatabaseEngine, Requirements

AVAILABILITY_RANK = {
    AvailabilityTier.STANDARD.value: 0,
    AvailabilityTier.HIGH.value: 1,
    AvailabilityTier.CRITICAL.value: 2,
}


class NoViableArchitecture(Exception):
    """No catalog combination can satisfy the requirements and budget."""


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _availability_supported(service: CatalogService, requested: str, category: str) -> bool:
    try:
        service_rank = AVAILABILITY_RANK[service.min_availability]
        requested_rank = AVAILABILITY_RANK[requested]
    except KeyError as exc:
        raise ValueError(
            f"unknown availability tier in catalog or requirements: {exc.args[0]}"
        ) from exc

    # Stateless compute is made highly available through two instances. Managed
    # storage/cache/CDN services are also acceptable with the HIGH requirement;
    # database and load-balancer options must explicitly advertise HIGH.
    if requested == AvailabilityTier.HIGH.value and category in {
        ComponentCategory.COMPUTE.value,
        ComponentCategory.STORAGE.value,
        ComponentCategory.CACHE.value,
        ComponentCategory.CDN.value,
    }:
        return service_rank >= AVAILABILITY_RANK[AvailabilityTier.STANDARD.value]
    return service_rank >= requested_rank


def filter_catalog(
    catalog: list[CatalogService], category: ComponentCategory, req: Requirements
) -> list[CatalogService]:
    """Return AWS services that satisfy hard capacity and availability constraints."""
    category_value = _value(category)
    requested_availability = _value(req.availability)
    return [
        service
        for service in catalog
        if service.provider == "aws"
        and service.category == category_value
        and _availability_supported(service, requested_availability, category_value)
        and (service.max_rpm is None or service.max_rpm >= req.requests_per_minute)
        and (service.max_users is None or service.max_users >= req.monthly_active_users)
    ]


def pick_cheapest(candidates: list[CatalogService], count: int = 1) -> CatalogService:
    """Select the cheapest candidate using its monthly catalog base price."""
    if not candidates:
        raise ValueError("cannot pick a service from an empty candidate list")
    if count <= 0:
        raise ValueError("count must be greater than zero")
    return min(
        candidates,
        key=lambda service: estimate_cost(
            service,
            count=count,
            size_gb=0 if service.pricing_model == PricingModel.PER_UNIT.value else None,
        ),
    )


def _database_matches(service: CatalogService, req: Requirements) -> bool:
    engine = _value(req.database)
    if engine == DatabaseEngine.POSTGRESQL.value:
        return "postgres" in service.id.lower() or "postgres" in service.display_name.lower()
    if engine == DatabaseEngine.MYSQL.value:
        return "mysql" in service.id.lower() or "mysql" in service.display_name.lower()
    return False


def _candidate_cost(service: CatalogService, req: Requirements, count: int) -> float:
    size_gb = req.storage_gb if service.pricing_model == PricingModel.PER_UNIT.value else None
    return estimate_cost(service, count=count, size_gb=size_gb)


def _select_service(
    catalog: list[CatalogService], category: ComponentCategory, req: Requirements, count: int
) -> CatalogService:
    candidates = filter_catalog(catalog, category, req)
    if category == ComponentCategory.DATABASE:
        candidates = [service for service in candidates if _database_matches(service, req)]
    if not candidates:
        raise NoViableArchitecture(
            f"catálogo insuficiente: no hay servicio {category.value} viable para "
            f"availability={_value(req.availability)}, usuarios={req.monthly_active_users} "
            f"y rpm={req.requests_per_minute}"
        )
    return min(candidates, key=lambda service: _candidate_cost(service, req, count))


def _required_categories(
    req: Requirements, compute_count: int
) -> list[tuple[ComponentCategory, int]]:
    categories: list[tuple[ComponentCategory, int]] = [
        (ComponentCategory.COMPUTE, compute_count),
    ]
    if _value(req.database) != DatabaseEngine.NONE.value:
        categories.append((ComponentCategory.DATABASE, 1))
    if req.storage_gb > 0:
        categories.append((ComponentCategory.STORAGE, 1))
    if _value(req.availability) != AvailabilityTier.STANDARD.value or compute_count > 1:
        categories.append((ComponentCategory.LOAD_BALANCER, 1))
    if _value(req.optimize_for) == "performance":
        categories.append((ComponentCategory.CACHE, 1))
    if _value(req.app_type) == "static_site":
        categories.append((ComponentCategory.CDN, 1))
    return categories


def _component_id(category: ComponentCategory) -> str:
    return {
        ComponentCategory.COMPUTE: "api-1",
        ComponentCategory.DATABASE: "db-1",
        ComponentCategory.STORAGE: "storage-1",
        ComponentCategory.LOAD_BALANCER: "lb-1",
        ComponentCategory.CACHE: "cache-1",
        ComponentCategory.CDN: "cdn-1",
    }[category]


def _config(category: ComponentCategory, req: Requirements) -> dict:
    if category == ComponentCategory.COMPUTE:
        return {"multi_az": _value(req.availability) != AvailabilityTier.STANDARD.value}
    if category == ComponentCategory.DATABASE:
        return {
            "engine": _value(req.database),
            "multi_az": _value(req.availability) != AvailabilityTier.STANDARD.value,
        }
    if category == ComponentCategory.STORAGE:
        return {"size_gb": req.storage_gb}
    return {}


def _complexity(category_count: int) -> Level:
    if category_count <= 2:
        return Level.LOW
    if category_count <= 4:
        return Level.MEDIUM
    return Level.HIGH


def _operational_overhead(services: Iterable[CatalogService]) -> Level:
    manual = sum(service.id.startswith("aws.ec2.") for service in services)
    if manual == 0:
        return Level.LOW
    if manual <= 2:
        return Level.MEDIUM
    return Level.HIGH


def _connections(components: list[Component]) -> list[Connection]:
    by_category = {component.category: component for component in components}
    result: list[Connection] = []

    if "load_balancer" in by_category and "compute" in by_category:
        result.append(Connection(source="lb-1", target="api-1", label="HTTP"))
    if "compute" in by_category:
        for category in ("database", "storage", "cache"):
            if category in by_category:
                label = "reads/writes" if category != "cache" else "cache"
                result.append(
                    Connection(source="api-1", target=by_category[category].id, label=label)
                )
    if "cdn" in by_category:
        target = "storage-1" if "storage" in by_category else "api-1"
        result.append(Connection(source="cdn-1", target=target, label="HTTP"))
    return result


def _decisions(components: list[Component], req: Requirements) -> list[Decision]:
    return [
        Decision(
            component_id=component.id,
            reasoning=(
                f"{component.display_name} cumple los límites declarados de usuarios y RPM; "
                f"la selección prioriza el menor costo mensual compatible con "
                f"availability={_value(req.availability)}."
            ),
            factors={
                "cost": "minimum viable catalog option",
                "availability": _value(req.availability),
            },
        )
        for component in components
    ]


def recommend(req: Requirements, catalog: list[CatalogService]) -> ArchSpec:
    """Build an ``ArchSpec`` without network calls, randomness, or mutation."""
    compute_count = 1 if _value(req.availability) == AvailabilityTier.STANDARD.value else 2
    selected: dict[ComponentCategory, tuple[CatalogService, int, float]] = {}
    running_cost = 0.0
    selected_categories: list[str] = []

    for category, count in _required_categories(req, compute_count):
        service = _select_service(catalog, category, req, count)
        cost = _candidate_cost(service, req, count)
        remaining = req.monthly_budget_usd - running_cost
        if cost > remaining + 1e-9:
            prior = "+".join(selected_categories) or "ninguna categoría"
            raise NoViableArchitecture(
                f"{category.value} mínimo viable cuesta ${cost:.2f}, pero solo quedan "
                f"${max(remaining, 0):.2f} de presupuesto tras {prior}"
            )
        selected[category] = (service, count, cost)
        running_cost = round(running_cost + cost, 2)
        selected_categories.append(category.value)

    output_order = [
        ComponentCategory.LOAD_BALANCER,
        ComponentCategory.COMPUTE,
        ComponentCategory.DATABASE,
        ComponentCategory.STORAGE,
        ComponentCategory.CACHE,
        ComponentCategory.CDN,
    ]
    components = [
        Component(
            id=_component_id(category),
            service_id=selected[category][0].id,
            category=category.value,
            display_name=selected[category][0].display_name,
            count=selected[category][1],
            config=_config(category, req),
            estimated_monthly_cost_usd=selected[category][2],
        )
        for category in output_order
        if category in selected
    ]
    services = [selected[category][0] for category in selected]
    total_cost = round(sum(component.estimated_monthly_cost_usd for component in components), 2)
    compute_service = selected[ComponentCategory.COMPUTE][0]
    compute_count = selected[ComponentCategory.COMPUTE][1]
    scalability = (
        Level.HIGH
        if compute_service.max_rpm is not None
        and compute_service.max_rpm * compute_count >= req.requests_per_minute * 2
        else Level.MEDIUM
    )
    availability_pct = {
        AvailabilityTier.STANDARD.value: 99.5,
        AvailabilityTier.HIGH.value: 99.9,
        AvailabilityTier.CRITICAL.value: 99.99,
    }[_value(req.availability)]
    score = ScoreCard(
        cost_usd_month=total_cost,
        complexity=_complexity(len(components)),
        scalability=scalability,
        availability_pct=availability_pct,
        operational_overhead=_operational_overhead(services),
    )
    identity = json.dumps(
        {
            "requirements": req.model_dump(mode="json"),
            "components": [component.model_dump(mode="json") for component in components],
        },
        sort_keys=True,
    ).encode("utf-8")
    stable_id = f"archspec-{hashlib.sha256(identity).hexdigest()[:12]}"
    return ArchSpec(
        id=stable_id,
        requirements=req.model_copy(deep=True),
        components=components,
        connections=_connections(components),
        decisions=_decisions(components, req),
        score=score,
        total_monthly_cost_usd=total_cost,
    )
