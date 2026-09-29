"""HTTP API for architecture generation and retrieval."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from api.db import ArchitectureRecord, get_db, init_db
from diagram.mermaid import to_mermaid
from engine.rule_engine import NoViableArchitecture, recommend
from schema.architecture import ArchSpec
from schema.catalog import CatalogService
from schema.requirements import Requirements

CATALOG_PATH = Path(__file__).parents[1] / "examples" / "catalog.aws.sample.json"
CATALOG = [
    CatalogService.model_validate(item)
    for item in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="InfraWise API",
    description="Deterministic cloud architecture recommendations.",
    version="0.2.0",
    lifespan=lifespan,
)

DbSession = Annotated[Session, Depends(get_db)]


def _load_architecture(architecture_id: str, db: Session) -> ArchSpec:
    record = db.get(ArchitectureRecord, architecture_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Architecture not found")
    return ArchSpec.model_validate(record.payload)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Container/readiness probe that does not expose infrastructure details."""
    return {"status": "ok"}


@app.post("/architectures", response_model=ArchSpec, status_code=201, tags=["architectures"])
def create_architecture(requirements: Requirements, db: DbSession) -> ArchSpec:
    try:
        spec = recommend(requirements, CATALOG)
    except NoViableArchitecture as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = db.get(ArchitectureRecord, spec.id)
    payload = spec.model_dump(mode="json")
    if record is None:
        record = ArchitectureRecord(
            id=spec.id,
            payload=payload,
            created_at=spec.created_at,
        )
        db.add(record)
    else:
        record.payload = payload
        record.created_at = spec.created_at
    db.commit()
    return spec


@app.get("/architectures/{architecture_id}", response_model=ArchSpec, tags=["architectures"])
def get_architecture(architecture_id: str, db: DbSession) -> ArchSpec:
    return _load_architecture(architecture_id, db)


@app.get(
    "/architectures/{architecture_id}/diagram",
    response_class=PlainTextResponse,
    responses={404: {"description": "Architecture not found"}},
    tags=["architectures"],
)
def get_architecture_diagram(architecture_id: str, db: DbSession) -> Response:
    spec = _load_architecture(architecture_id, db)
    return PlainTextResponse(to_mermaid(spec), media_type="text/plain")
