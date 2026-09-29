import json
from pathlib import Path

from diagram.mermaid import to_mermaid
from engine.rule_engine import recommend
from schema.architecture import ArchSpec
from schema.catalog import CatalogService
from schema.requirements import Requirements

EXAMPLES = Path(__file__).parents[1] / "examples"


def load_spec() -> ArchSpec:
    requirements = Requirements.model_validate(
        json.loads((EXAMPLES / "requirements.example.json").read_text(encoding="utf-8"))
    )
    catalog = [
        CatalogService.model_validate(item)
        for item in json.loads((EXAMPLES / "catalog.aws.sample.json").read_text(encoding="utf-8"))
    ]
    return recommend(requirements, catalog)


def test_mermaid_contains_all_nodes_and_connections():
    spec = load_spec()

    diagram = to_mermaid(spec)

    assert diagram.startswith("graph TD\n")
    for component in spec.components:
        assert component.id in diagram
    assert "lb-1 -->|HTTP| api-1" in diagram
    assert "api-1 -->|reads/writes| db-1" in diagram


def test_mermaid_escapes_display_labels():
    spec = load_spec().model_copy(
        update={
            "components": [
                load_spec()
                .components[0]
                .model_copy(update={"display_name": 'LB "public"\nprimary'})
            ]
        }
    )

    diagram = to_mermaid(spec)

    assert '\\"public\\"' in diagram
    assert "\\n" in diagram
