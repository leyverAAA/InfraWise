import json
from pathlib import Path

import pytest

from engine.cost_engine import estimate_cost
from schema.catalog import CatalogService

CATALOG_PATH = Path(__file__).parents[1] / "examples" / "catalog.aws.sample.json"


def service(service_id: str) -> CatalogService:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return CatalogService.model_validate(next(item for item in data if item["id"] == service_id))


def test_flat_monthly_cost_scales_by_count():
    assert estimate_cost(service("aws.alb"), count=2) == 32.0


def test_instance_hour_uses_catalog_monthly_price():
    assert estimate_cost(service("aws.ec2.t3.small"), count=2) == 30.36


def test_per_unit_cost_requires_and_uses_size():
    assert estimate_cost(service("aws.s3.standard"), size_gb=50) == 1.15


def test_per_unit_without_size_is_explicitly_invalid():
    with pytest.raises(ValueError, match="size_gb"):
        estimate_cost(service("aws.s3.standard"))


def test_per_unit_without_unit_price_is_catalog_error():
    s3 = service("aws.s3.standard").model_copy(update={"unit_price_usd": None})
    with pytest.raises(ValueError, match="unit_price_usd"):
        estimate_cost(s3, size_gb=50)


def test_non_positive_count_is_invalid():
    with pytest.raises(ValueError, match="count"):
        estimate_cost(service("aws.alb"), count=0)
