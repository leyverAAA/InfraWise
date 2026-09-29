<div align="center">

# InfraWise

### FinOps & Cloud Architecture Advisor

**Convierte requisitos de negocio en una arquitectura Cloud justificable, reproducible y con costo estimado.**

[![Fase](https://img.shields.io/badge/fase-3%20%2F%205%20implementada-4EAA25)](ROADMAP.md)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-fase%202-009688?logo=fastapi&logoColor=white)](ROADMAP.md)
[![Terraform](https://img.shields.io/badge/export-Terraform-fase%205-844FBA?logo=terraform&logoColor=white)](ROADMAP.md)
[![AI](https://img.shields.io/badge/ai-Ollama%20%2B%20template%20fallback-4EAA25)](ai/)
[![Determinista](https://img.shields.io/badge/motor-100%25%20determinista-557C94)](engine/rule_engine.py)
[![Tests](https://img.shields.io/badge/tests-34%20pasando-4C1?logo=pytest&logoColor=white)](tests/)

</div>

---

**InfraWise** es un motor determinista que convierte los requisitos de una aplicación —usuarios, tráfico, motor de base de datos, disponibilidad, presupuesto y optimización— en una **arquitectura Cloud concreta**, con costo mensual estimado, conexiones, un score explicable y una justificación por cada componente.

El núcleo de dominio vive en módulos Python separados —esquema, motor de reglas y motor de costos— y se comunica mediante **modelos tipados** (`Requirements`, `CatalogService`, `ArchSpec`). La API y la persistencia son una capa externa: el dominio sigue sin llamadas de red ni SDK de proveedor, y la misma entrada produce la misma arquitectura.

> **Importante:** este es un proyecto de aprendizaje en fase temprana. La Fase 3 ya añade explicaciones con Ollama y un fallback determinista sin red. El README documenta lo que **realmente corre hoy** y separa explícitamente lo pendiente; la ejecución de Docker queda pendiente de validar cuando el daemon esté disponible.

---

## Índice

- [Qué problema resuelve](#qué-problema-resuelve)
- [El objetivo](#el-objetivo)
- [Qué incluye](#qué-incluye)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Arquitectura](#arquitectura)
- [Flujo operativo](#flujo-operativo)
- [API HTTP](#api-http)
- [IA local y fallback](#ia-local-y-fallback)
- [Docker y Compose](#docker-y-compose)
- [Tecnologías](#tecnologías)
- [Seguridad](#seguridad)
- [Salidas y observabilidad](#salidas-y-observabilidad)
- [Testing](#testing)
- [Instalación](#instalación)
- [Uso rápido](#uso-rápido)
- [CI](#ci)
- [Ejemplo real](#ejemplo-real)
- [Estado del proyecto](#estado-del-proyecto)
- [Configuración](#configuración)
- [Documentación](#documentación)
- [Contacto](#contacto)

---

## Qué problema resuelve

Diseñar infraestructura Cloud no es elegir "lo mejor". Es una restricción mutua entre cinco variables que rara vez se optimizan juntas:

```text
Costo  +  Escalabilidad  +  Disponibilidad  +  Seguridad  +  Complejidad Operativa
                            ↓
                    ¿Qué arquitectura?
```

En la práctica esto produce dos extremos:

| Problema | Qué pasa |
| :--- | :--- |
| **Sobredimensionado** | Se despliega Kubernetes para una API de 500 usuarios porque "es lo que se usa". El costo y la complejidad no lo justifican. |
| **Subdimensionado** | Una sola instancia EC2 porque "es solo un MVP". Funciona hasta que cae, y con ella la base de datos. |

InfraWise parte de una premisa explícita:

> **La mejor arquitectura no es la más grande ni la más moderna. Es la que tiene sentido para los requisitos, la escala y las restricciones del sistema.**

El motor no optimiza una dimensión: **filtra** el catálogo por las restricciones duras (capacidad, disponibilidad, presupuesto) y luego elige, dentro de lo técnicamente viable, **la opción más barata**.

---

## El objetivo

Demostrar que un motor de arquitectura Cloud puede ser:

- **Determinista** — misma entrada, mismo `ArchSpec`. El `id` es un SHA-256 de los requisitos más los componentes, no un UUID aleatorio.
- **Puro** — sin red, sin IA, sin I/O. El dominio se prueba con `assert`, no con mocks.
- **Explicable** — cada componente trae una `Decision` con su razonamiento y sus factores.
- **Fiel al presupuesto** — nunca devuelve una arquitectura que exceda el presupuesto mensual declarado. Si no alcanza, lo dice y por cuánto.

---

## Qué incluye

```text
┌───────────────────────────────────────────────────────────────┐
│                    PROJECT HIGHLIGHTS                        │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│ Pydantic     │ Determinista │ 11 servicios│ API HTTP         │
│ schemas      │ rule engine  │ catálogo AWS│ + Mermaid        │
├──────────────┼──────────────┼──────────────┼──────────────────┤
│ 3 modelos    │ Presupuesto  │ ScoreCard    │ 34 tests         │
│ de precio    │ validado     │ explicable   │ 91% coverage     │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

### Esquema — `schema/`

Modelos Pydantic que son el contrato de todo el sistema.

- **`Requirements`** — la entrada. Deliberadamente **agnóstico del proveedor**: no menciona AWS, EC2 ni RDS. Ese mapeo es trabajo del Rule Engine, y mantener la frontera hace que "agregar GCP después" sea aditivo y no una reescritura.
- **`CatalogService`** — una opción de servicio normalizada, con su modelo de precio, su precio base mensual, su precio unitario opcional y sus límites de capacidad declarados.
- **`ArchSpec`** — el artefacto único que recorre el sistema. Es una **instantánea inmutable**: incluye una copia de los requisitos que la produjeron, así que siempre se puede responder *"¿qué recomendamos el 3 de marzo y por qué?"*.

| Tipo | Rol |
| :--- | :--- |
| `Requirements` | Entrada: 9 campos validados por Pydantic |
| `CatalogService` | Fila del catálogo: precio, capacidad, disponibilidad mínima |
| `ArchSpec` | Salida: componentes, conexiones, decisiones, score, costo total |
| `Component` | Un recurso con `count`, `config` y costo estimado |
| `Connection` | Una arista `source → target` con etiqueta (`HTTP`, `reads/writes`) |
| `Decision` | La justificación de un componente, con sus `factors` |
| `ScoreCard` | Los 5 ejes de evaluación de la arquitectura |

### Motor de costos — `engine/cost_engine.py`

Una función pura, sin I/O ni dependencia de SDK:

```python
estimate_cost(service: CatalogService, count: int = 1, size_gb: float | None = None) -> float
```

| Modelo de precio | Cálculo | Ejemplo en el catálogo |
| :--- | :--- | :--- |
| `flat_monthly` | `base_monthly_usd * count` | ALB `$16.00` |
| `instance_hour` | `base_monthly_usd * count` (ya normalizado a mensual) | EC2 t3.small `$15.18` |
| `per_unit` | `unit_price_usd * size_gb * count` | S3 Standard `$0.023/GB` |

Un error de catálogo **falla de forma explícita** en lugar de convertirse en costo cero: `per_unit` sin `size_gb` lanza `ValueError`, y `per_unit` sin `unit_price_usd` lanza `CostCatalogError`. El resultado se redondea a centavos para mantener una salida estable.

### Motor de reglas — `engine/rule_engine.py`

El cerebro determinista. Tres funciones públicas:

```python
filter_catalog(catalog, category, req) -> list[CatalogService]   # restricciones duras
pick_cheapest(candidates, count=1)  -> CatalogService            # menor costo viable
recommend(req, catalog)             -> ArchSpec                  # la arquitectura completa
```

**Filtro (restricciones duras, no preferencias):**

- `provider == "aws"` — hardcodeado en v1, a propósito.
- La categoría coincide.
- `min_availability` del servicio es compatible con el nivel pedido, usando una tabla ordenada `standard < high < critical` — **no** una cadena de `if`, y **no** comparación lexicográfica de strings.
- `max_rpm >= req.requests_per_minute` y `max_users >= req.monthly_active_users`, cuando el servicio los declara. S3 y ALB no los declaran, y eso es intencional.

> **Matiz importante para `HIGH`:** compute stateless se vuelve altamente disponible con dos instancias, y storage/cache/CDN administrados aceptan la garantía del catálogo. Pero **database y load_balancer deben declarar `HIGH` explícitamente** — es la razón por la que `availability=high` fuerza RDS Multi-AZ en lugar de aceptar la single-AZ por ser más barata.

**Reglas de inclusión de categorías:**

| Categoría | Se incluye cuando |
| :--- | :--- |
| `compute` | siempre |
| `database` | `req.database != none` |
| `storage` | `req.storage_gb > 0` |
| `load_balancer` | `availability != standard` **o** el compute necesita `count > 1` |
| `cache` | `req.optimize_for == performance` |
| `cdn` | `req.app_type == static_site` |

**Presupuesto como restricción, no como sugerencia:** el motor acumula el costo de cada opción mínima viable y lanza `NoViableArchitecture` nombrando la categoría que rompió el presupuesto y el saldo restante. El único resultado permitido es un `ArchSpec` dentro del presupuesto o un error explicable — nunca un tercero.

**ScoreCard**, con heurísticas simples y documentadas:

| Eje | Regla |
| :--- | :--- |
| `cost_usd_month` | Suma de los componentes seleccionados |
| `complexity` | `LOW` ≤2 categorías · `MEDIUM` 3–4 · `HIGH` 5+ |
| `scalability` | `HIGH` si el compute tiene ≥2× de margen entre `max_rpm` y el tráfico pedido |
| `availability_pct` | `99.5` standard · `99.9` high · `99.99` critical |
| `operational_overhead` | Cuenta los servicios que requieren mantenimiento manual (hoy, EC2) |

### API, persistencia y diagramas — Fase 2

La capa HTTP reutiliza `recommend()` sin duplicar reglas de negocio:

| Endpoint | Resultado |
| :--- | :--- |
| `POST /architectures` | Valida `Requirements`, genera, persiste y devuelve un `ArchSpec` con `201`. |
| `GET /architectures/{id}` | Recupera el snapshot persistido o devuelve `404`. |
| `GET /architectures/{id}/diagram` | Devuelve el diagrama Mermaid como `text/plain` o `404`. |
| `GET /health` | Healthcheck mínimo para desarrollo y contenedores. |
| `/docs` · `/openapi.json` | Documentación interactiva y contrato OpenAPI generado por FastAPI. |

La persistencia usa una tabla `architectures` con `id`, `payload` JSON/JSONB y `created_at`. SQLite es el valor por defecto para desarrollo local; Compose utiliza PostgreSQL 16 mediante `DATABASE_URL`.

`diagram/mermaid.py` mantiene el serializador como una función pura: no abre conexiones ni realiza I/O, y escapa etiquetas antes de producir los nodos y conexiones.

### Catálogo de ejemplo

`examples/catalog.aws.sample.json` — 11 servicios AWS con precios de lista on-demand de `us-east-1` (2026), convertidos a mensual con 730 h/mes.

| Servicio | Categoría | $/mes | RPM máx | Usuarios máx | Disponibilidad mín. |
| :--- | :--- | :--- | :--- | :--- | :--- |
| EC2 t3.micro | compute | 7.59 | 500 | 1 000 | standard |
| EC2 t3.small | compute | 15.18 | 1 500 | 5 000 | standard |
| EC2 t3.medium | compute | 30.37 | 4 000 | 15 000 | standard |
| ElastiCache Redis t3.micro | cache | 12.41 | — | — | standard |
| RDS PostgreSQL db.t3.micro | database | 15.00 | 800 | 2 000 | standard |
| RDS PostgreSQL db.t3.small | database | 30.00 | 2 000 | 8 000 | standard |
| RDS PostgreSQL db.t3.small (Multi-AZ) | database | 60.00 | 2 000 | 8 000 | **high** |
| RDS PostgreSQL db.t3.medium (Multi-AZ) | database | 120.00 | 5 000 | 20 000 | **high** |
| S3 Standard | storage | 0.023 /GB | — | — | standard |
| Application Load Balancer | load_balancer | 16.00 | — | — | **high** |
| CloudFront | cdn | 0.085 /GB out | — | — | standard |

---

## Estructura del proyecto

```text
InfraWise/
├── .gitignore                     # caches, .env, secrets y bases locales
├── .dockerignore                  # contexto Docker sin secretos ni artefactos
├── pyproject.toml                 # Dependencias, pytest, ruff, black
├── uv.lock                        # Grafo de dependencias fijado
├── README.md
├── ROADMAP.md                     # Fases 0–5, cada una con milestone
├── PHASE1_REPORT.md               # Evidencia de la Fase 1 (tests, cobertura, decisiones)
├── PHASE2_REPORT.md               # Evidencia de API, persistencia, Mermaid y Compose
│
├── schema/                        # ✅ CONTRATOS DEL DOMINIO
│   ├── requirements.py            # Requirements + 4 enums
│   ├── catalog.py                 # CatalogService, PricingModel, ComponentCategory
│   └── architecture.py            # ArchSpec, Component, Connection, Decision, ScoreCard
│
├── engine/                        # ✅ MOTOR PURO
│   ├── cost_engine.py             # estimate_cost()
│   └── rule_engine.py             # filter_catalog(), pick_cheapest(), recommend()
│
├── examples/                      # ✅ FIXTURES VERIFICADOS
│   ├── catalog.aws.sample.json    # 11 servicios AWS
│   ├── requirements.example.json  # la entrada de ejemplo
│   ├── architecture.example.json  # el golden fixture ($107.51)
│   └── _generate_examples.py      # regenera los fixtures (solo stdlib)
│
├── tests/                         # ✅ 28 TESTS, 94% COVERAGE total de Fase 2
│   ├── test_cost_engine.py        # los 3 modelos de precio + casos borde
│   ├── test_api.py                # endpoints, validación y persistencia SQLite
│   ├── test_diagram.py             # nodos, conexiones y escaping Mermaid
│   └── test_rule_engine.py        # golden fixture, reglas, property test
│
├── api/main.py                    # ✅ FASE 2 — endpoints FastAPI
├── api/db.py                      # ✅ SQLAlchemy + SQLite/PostgreSQL JSONB
├── diagram/mermaid.py             # ✅ FASE 2 — ArchSpec → Mermaid
├── ai/
│   ├── base.py                    # ✅ AIExplainer + AIProviderUnavailable
│   ├── ollama_provider.py         # ✅ Ollama JSON contract + timeout
│   ├── template_provider.py       # ✅ fallback determinista en español
│   └── factory.py                 # ✅ selección + healthcheck + fallback
├── export/terraform.py            # ⬜ FASE 5 — ArchSpec → .tf (vacío)
├── frontend/                      # ⬜ FASE 4 — Next.js (vacío)
├── Dockerfile                     # ✅ Python 3.12, healthcheck, usuario no root
├── docker-compose.yml              # ✅ API + PostgreSQL 16 + volumen persistente
└── .github/workflows/ci.yml        # ✅ lint, tests, Compose config y build
```

> ✅ construido y probado · 🟡 implementado pero con validación externa pendiente · ⬜ reservado

---

## Arquitectura

El `ArchSpec` es el único contrato entre etapas. Cada etapa **lo lee y devuelve uno nuevo, más completo**. Ninguna lo muta en sitio, ninguna recalcula requisitos ni vuelve a elegir servicios desde cero.

```mermaid
flowchart TD
    U["Requisitos en lenguaje natural"] --> REQS["Requirements<br/><i>schema/requirements.py</i>"]
    REQS --> CAT["CatalogService<br/><i>schema/catalog.py</i>"]
    CAT --> RE["Rule Engine<br/><i>engine/rule_engine.py</i>"]
    RE --> CE["Cost Engine<br/><i>engine/cost_engine.py</i>"]
    CE --> SPEC["ArchSpec<br/><i>schema/architecture.py</i>"]
    SPEC --> DIAG["Mermaid<br/><i>diagram/</i> ✅"]
    SPEC --> EXPL["AI Explainer<br/><i>ai/</i> ✅ Ollama/template"]
    SPEC --> TF["Terraform .tf<br/><i>export/</i> ⬜"]
    SPEC --> UI["Frontend<br/><i>frontend/</i> ⬜"]
    REQS -.-> API["FastAPI<br/><i>api/</i> ✅"]
    API --> DB["PostgreSQL / SQLite<br/><i>api/db.py</i> ✅"]
```

### Por qué un artefacto y no varios

Esa inmutabilidad es lo que después hace triviales dos cosas:

- **Diff "antes vs. después" de una optimización** — `ArchSpec` v1 contra v2, misma familia de `id`.
- **Historial de auditoría** — el `ArchSpec` viejo y sus requisitos nunca cambiaron, así que la recomendación es siempre reconstruible.

### Pipeline de calidad

```mermaid
flowchart LR
    Code["Cambio en código o configuración"] --> FMT["black --check<br/>ruff check"]
    FMT --> VAL["pytest -q"]
    VAL --> COV["pytest --cov=engine --cov=api<br/>--cov=diagram --cov=schema --cov=ai"]
    COV --> COMPOSE["docker compose config"]
    COMPOSE --> IMAGE["docker build"]
    IMAGE --> GREEN{"¿Verde?"}
    GREEN -->|Sí| Merge["Listo para review"]
    GREEN -->|No| Fix["Corregir"]
    Fix --> FMT
```

---

## Flujo operativo

### Aprovisionamiento del dominio

```text
Requisitos → filter_catalog → pick_cheapest → Cost Engine → ArchSpec
```

### Verificación tras el recommend

```text
ArchSpec.id                      → identificador estable y reproducible
ArchSpec.total_monthly_cost_usd  → costo mensual de la arquitectura
ArchSpec.score                   → los 5 ejes, en una sola línea
ArchSpec.decisions               → por qué cada componente
```

### Depuración de una recomendación

```text
filter_catalog(catalog, ComponentCategory.DATABASE, req)  → ¿qué sobrevivió al filtro?
```

Si la lista viene vacía o incompleta, el problema está en los requisitos (capacidad o disponibilidad), no en el selector. Es el primer paso de debugging más útil del motor.

---

## Tecnologías

| Tecnología | Uso |
| :--- | :--- |
| Python `>=3.11,<3.13` | Lenguaje base. `StrEnum` y `datetime.UTC` exigen 3.11+. |
| Pydantic `>=2.7,<3` | Validación y serialización de los 4 modelos del dominio. |
| FastAPI `>=0.115,<0.120` | API HTTP, validación, OpenAPI y Swagger. |
| SQLAlchemy `>=2,<3` | Persistencia de snapshots `ArchSpec`. |
| Uvicorn | Servidor ASGI local y de contenedor. |
| Psycopg | Driver PostgreSQL para Compose. |
| Pytest `>=8,<9` | Suite de 34 tests, incluido un property test con semilla fija. |
| Pytest-cov `>=5,<6` | Reporte de cobertura de `engine`, `api`, `diagram`, `schema` e `ai`. |
| Ruff `>=0.6,<1` | Lint. Reglas `E`, `F`, `I`, `UP`, `B`. Línea de 100. |
| Black `>=24,<26` | Formato. Línea de 100, `py311`. |
| Hatchling | Build backend del paquete `infrawise`. |
| uv | Gestión de entorno y lockfile. |
| Docker + Compose | Fase 2 — API + PostgreSQL reproducibles |
| GitHub Actions | Quality gates y build de imagen |
| Ollama | Fase 3 — explicar `decisions` con un modelo local opcional |
| Next.js + React Flow | ⬜ Fase 4 — formulario y editor visual de arquitecturas |
| Terraform | ⬜ Fase 5 — exportar el `ArchSpec` a `.tf` |

> El dominio mantiene una dependencia mínima y pura (`pydantic`). FastAPI, SQLAlchemy, Uvicorn y Psycopg pertenecen a la capa externa de API/persistencia; Ruff, Black, Pytest y uv sostienen los quality gates.

---

## Seguridad

- **Sin llamadas de red en el dominio.** `engine/` y `schema/` no importan ningún SDK de AWS, ni `boto3`, ni `requests`. Eso elimina de raíz la clase de problemas donde un test necesita credenciales o una red inestable. La red queda limitada a la capa HTTP y a la conexión configurable de persistencia.
- **Sin secretos en el repositorio.** `.env` y `.env.*` están en `.gitignore` (con `!.env.example` como excepción explícita). No hay claves, tokens ni credenciales AWS en el código.
- **Contraseñas y datos sensibles como `SecretStr`.** Cuando la Fase 4 exponga la API, los campos de contraseña se tipan como `SecretStr` para que Pydantic los redacte en logs y en `model_dump()`.
- **`CORS` sin comodines en producción.** La API actual no habilita CORS todavía; la Fase 4 deberá permitir explícitamente el dominio del frontend y no usar `allow_origins=["*"]`.
- **Contenedor con menor privilegio.** El Dockerfile ejecuta Uvicorn como `appuser`, usa una imagen slim y excluye secretos y bases locales mediante `.dockerignore`.
- **Credenciales de desarrollo visibles.** Compose usa `infrawise_dev_only` como valor local overrideable por `.env`; no debe reutilizarse en producción.
- **Sin datos personales de usuarios.** El modelo `Requirements` describe una aplicación, nunca a una persona. No hay PII en la base de datos.
- **Presupuesto como puerta de seguridad.** Una arquitectura que excede el presupuesto declarado nunca se devuelve, ni siquiera "por si acaso". El error nombra la categoría y el faltante.
- **Catálogo como datos, no como código.** Agregar un servicio o cambiar un precio es editar un JSON versionado y auditable, no desplegar código.

---

## Salidas y observabilidad

`ArchSpec` es a la vez la salida y el registro de auditoría. Para inspeccionar una decisión sin pasar por el `recommend()` completo, llama al filtro directamente. Para inspeccionar una arquitectura guardada, usa la API o consulta el endpoint Mermaid:

```python
# ¿Qué servicios de base de datos sobreviven al filtro con estos requisitos?
import json
from pathlib import Path

from engine.rule_engine import filter_catalog
from schema.catalog import CatalogService, ComponentCategory
from schema.requirements import Requirements

EXAMPLES = Path("examples")
catalog = [
    CatalogService.model_validate(item)
    for item in json.loads((EXAMPLES / "catalog.aws.sample.json").read_text(encoding="utf-8"))
]
req = Requirements.model_validate(
    json.loads((EXAMPLES / "requirements.example.json").read_text(encoding="utf-8"))
)

print([c.id for c in filter_catalog(catalog, ComponentCategory.DATABASE, req)])
# ['aws.rds.postgres.t3.small.multiaz', 'aws.rds.postgres.t3.medium.multiaz']
```

Esa lista es la explicación completa de por qué la base de datos no puede ser single-AZ: `availability=high` eliminó las dos opciones `standard` antes de que el selector de precio llegara a evaluarlas. Si la lista viniera vacía, el problema está en los requisitos — no en el selector.

Para el resto del sistema:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
pytest -q                                              # estado del dominio
pytest --cov=engine --cov=api --cov=diagram --cov=schema --cov=ai --cov-report=term-missing   # cobertura línea por línea
ruff check .                                          # lint
black --check .                                       # formato
docker compose config --quiet                         # Compose válido
```

`created_at` registra el momento en que se creó la instantánea; el `id` es un hash del contenido. Son deliberadamente independientes: el mismo contenido genera el mismo `id` aunque se genere en otra fecha.

---

## Testing

34 tests, 91 % de cobertura sobre 472 statements. La validación de dominio, API y providers es local y reproducible; **no requiere credenciales de AWS, PostgreSQL ni Ollama para la suite**: los tests de persistencia usan SQLite en memoria y el provider de templates no usa red.

```bash
uv run --extra dev pytest --cov=engine --cov=api --cov=diagram --cov=schema --cov=ai --cov-report=term-missing -q
```

| Archivo | Qué cubre |
| :--- | :--- |
| `tests/test_cost_engine.py` | Los 3 modelos de precio, `count <= 0`, `per_unit` sin `size_gb`, `per_unit` sin `unit_price_usd`. |
| `tests/test_rule_engine.py` | Golden fixture, filtro por capacidad/disponibilidad, selección más barata, las 6 categorías, conexiones, cache/CDN, presupuesto insuficiente, catálogo insuficiente para `CRITICAL`, property test. |
| `tests/test_api.py` | POST/GET, persistencia, `422` de dominio y validación, `404`, health del flujo y endpoint de diagrama. |
| `tests/test_diagram.py` | Nodos, conexiones, encabezado Mermaid y escaping de etiquetas. |
| `tests/test_ai.py` | Contrato de providers, prompt acotado, fallback de factory y respuestas inválidas de Ollama. |

Tres pruebas merecen atención porque son la especificación ejecutable del dominio:

```text
test_matches_example_fixture
    Compara componentes {service_id, category, count} contra architecture.example.json
    — NO los costos exactos, que se mueven si se ajustan precios del catálogo.

test_never_exceeds_budget_for_valid_random_inputs
    50 Requirements aleatorios con semilla fija (20260928): o devuelve un ArchSpec
    dentro del presupuesto, o lanza NoViableArchitecture. Nunca un tercer resultado.

test_critical_availability_reports_catalog_gap
    availability=critical con un catálogo que solo llega a "high" debe dar un error
    de "catálogo insuficiente" — no un KeyError genérico.
```

La semilla fija es lo que hace que CI sea determinista: 50 casos property-based sin flakiness.

---

## Instalación

**Requisitos:** Python `3.11` o `3.12`, y [uv](https://docs.astral.sh/uv/).

```bash
git clone <tu-url-del-repo>.git
cd InfraWise
uv sync --extra dev       # crea .venv, instala API, persistencia y herramientas de calidad
```

> `uv.lock` fija el grafo de dependencias completo. Se commitea a propósito: es lo que garantiza que tu máquina, CI y un despliegue futuro ejecuten exactamente las mismas versiones.

<details>
<summary>Alternativa sin uv</summary>

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```
</details>

---

## Uso rápido

```bash
# 1. Ejecuta la suite
uv run --extra dev pytest -q

# 2. Regenera y valida los fixtures del ejemplo
uv run python examples/_generate_examples.py
#   → OK — total_monthly_cost_usd=107.51 (budget=150)

# 3. Quality gates antes de abrir un PR
uv run --extra dev ruff check .
uv run --extra dev black --check .
uv run --extra dev pytest --cov=engine --cov=api --cov=diagram --cov=schema --cov=ai -q
docker compose config --quiet
```

Y para tu propia entrada, la superficie real del motor cabe en un archivo de 20 líneas — `playground.py`:

```python
import json
from pathlib import Path

from engine.rule_engine import recommend
from schema.catalog import CatalogService
from schema.requirements import Requirements

EXAMPLES = Path("examples")
catalog = [
    CatalogService.model_validate(item)
    for item in json.loads((EXAMPLES / "catalog.aws.sample.json").read_text(encoding="utf-8"))
]

spec = recommend(
    Requirements(
        app_type="web_api",
        monthly_active_users=5000,
        requests_per_minute=300,
        database="postgresql",
        storage_gb=50,
        availability="high",
        monthly_budget_usd=150,
    ),
    catalog,
)

print(spec.id, spec.total_monthly_cost_usd)      # archspec-341170a3e023 107.51
for c in spec.components:
    print(f"  {c.id:11} {c.display_name:38} x{c.count}  ${c.estimated_monthly_cost_usd}")
for d in spec.decisions:
    print(f"  {d.component_id}: {d.reasoning}")
```

```bash
uv run python playground.py
```

Los dos únicos puntos de entrada del dominio son `recommend()` y `filter_catalog()`. No hay más superficie que aprender hasta la Fase 2.

> No hay `terraform apply` todavía: la exportación a `.tf` es la Fase 5. Hoy el único "despliegue" es producir y verificar un `ArchSpec`.

---

## Ejemplo real

Entrada — `examples/requirements.example.json`:

```json
{
  "app_type": "web_api",
  "monthly_active_users": 5000,
  "requests_per_minute": 300,
  "database": "postgresql",
  "storage_gb": 50,
  "availability": "high",
  "monthly_budget_usd": 150,
  "region": "us-east-1",
  "optimize_for": "balanced"
}
```

Salida de `recommend()` — verificada ejecutando el motor:

```text
id:     archspec-341170a3e023
total:  $107.51 /mes   (presupuesto: $150 → 28% de margen)

  lb-1        Application Load Balancer               x1    $16.00
  api-1       EC2 t3.small                            x2    $30.36
  db-1        RDS PostgreSQL db.t3.small (Multi-AZ)   x1    $60.00
  storage-1   S3 Standard                             x1     $1.15

  lb-1 -> api-1       (HTTP)
  api-1 -> db-1       (reads/writes)
  api-1 -> storage-1  (reads/writes)

score: complexity=medium  scalability=high
       availability=99.9%  operational_overhead=medium
```

Tres decisiones que explican el resultado:

```text
1. DOS t3.small, no un t3.medium
   Mismo costo por capacidad práctica que un t3.medium ($30.36 vs $30.37),
   pero availability=high prohíbe el punto único de falla. Con el LB ya
   presente, la segunda instancia es redundancia, no capacidad desperdiciada.

2. RDS Multi-AZ, no single-AZ
   Es la única categoría donde HIGH no es negociable: el catálogo declara
   min_availability="high" en la variante Multi-AZ. db.t3.medium quedaría
   sobrada a 5 000 usuarios / 300 rpm, así que se elige la más barata
   que cumple → $60 de ahorro frente a la opción siguiente.

3. El presupuesto nunca se excede
   Con monthly_budget_usd=10 el motor responde:
   "compute mínimo viable cuesta $30.36, pero solo quedan $10.00 de
    presupuesto tras ninguna categoría"

   Con availability=critical, sin catálogo que lo soporte:
   "catálogo insuficiente: no hay servicio compute viable para
    availability=critical, usuarios=5000 y rpm=300"
```

Ese último mensaje es el que la API convierte en `422` con una sugerencia accionable, en lugar de un `500` genérico.

---

## API HTTP

La API se inicia en desarrollo con SQLite local:

```bash
uv run uvicorn api.main:app --reload
```

Después, abre [`http://localhost:8000/docs`](http://localhost:8000/docs) para probar el contrato OpenAPI.

Crear una arquitectura usando el fixture del proyecto:

```bash
curl -X POST http://localhost:8000/architectures \
  -H "Content-Type: application/json" \
  --data @examples/requirements.example.json
```

La respuesta contiene el `id`, los componentes, conexiones, decisiones, score y costo total. El `id` es estable para la misma entrada; publicar de nuevo la misma recomendación actualiza el snapshot en lugar de crear una fila duplicada.

```bash
curl http://localhost:8000/architectures/<ID>
curl http://localhost:8000/architectures/<ID>/diagram
```

Errores esperados:

- `422`: requisitos inválidos o no existe una arquitectura viable dentro del catálogo/presupuesto.
- `404`: no existe el `ArchSpec` solicitado.

### Persistencia local

Sin `DATABASE_URL`, la API usa `sqlite:///./infrawise.db`. Para PostgreSQL, configura por ejemplo:

```bash
DATABASE_URL=postgresql+psycopg://infrawise:infrawise_dev_only@localhost:5432/infrawise
```

El payload completo del `ArchSpec` se conserva en una columna JSON/JSONB para mantener el historial auditable sin duplicar todavía el modelo en muchas columnas.

---

## IA local y fallback

La Fase 3 agrega explicaciones sin permitir que un modelo cambie la arquitectura calculada por el Rule Engine.

```text
ArchSpec (components + connections + factores)
                    │
                    ▼
              AIExplainer
              ┌─────┴─────┐
              ▼           ▼
          Ollama       Template
        (opcional)   (determinista)
              └─────┬─────┘
                    ▼
          ArchSpec + decisions
```

### Contrato de provider

`ai/base.py` define `AIExplainer.explain(spec) -> list[Decision]`. El contrato exige exactamente una `Decision` por componente. Los providers solo producen explicaciones: `components`, `connections`, costos, cantidades y factores siguen perteneciendo al resultado determinista del Rule Engine.

### Ollama

`OllamaExplainer` utiliza por defecto:

- URL: `http://localhost:11434`;
- modelo: `llama3.2`;
- endpoint: `/api/chat`;
- timeout: 4 segundos, limitado al rango 3–5 segundos;
- temperatura: `0.2`;
- respuesta JSON validada antes de persistirse.

El prompt envía únicamente los componentes y factores de decisión. El system prompt ordena explícitamente responder en español y no sugerir servicios que no estén en la arquitectura.

Si Ollama devuelve un error, JSON inválido, una cantidad incorrecta de decisiones o IDs de componentes distintos, se lanza `AIProviderUnavailable` y la API usa el fallback.

### Fallback determinista

`TemplateExplainer` no usa red ni modelo externo. Genera razonamientos reproducibles en español a partir de la categoría, el costo y los factores ya calculados por el Rule Engine. Por eso la misma request sigue funcionando aunque Ollama esté apagado, no tenga el modelo descargado o supere el timeout.

`ai/factory.py` lee `AI_PROVIDER`:

| Valor | Comportamiento |
| :--- | :--- |
| `ollama` o vacío | Ejecuta un healthcheck y usa Ollama si responde; si no, usa templates. |
| `template` | Usa directamente `TemplateExplainer`, útil para CI y demos sin red. |
| Otro valor | Registra un warning y usa templates de forma segura. |

Variables opcionales:

```bash
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT_SECONDS=4
```

La API vuelve a intentar el fallback ante una falla durante la llamada, incluso si el healthcheck inicial había sido exitoso. Las `decisions` ya generadas se persisten junto con el `ArchSpec`.

---

## Docker y Compose

La topología de desarrollo contiene dos servicios:

```text
api: FastAPI + Uvicorn :8000
  │
  └── DATABASE_URL → db
                         PostgreSQL 16
                         volumen postgres_data
```

Arranque recomendado:

```bash
docker compose config --quiet   # validar antes de levantar
docker compose up --build
```

La API espera el healthcheck de PostgreSQL antes de iniciar. El Dockerfile usa `python:3.12-slim`, instala sin cache, ejecuta como `appuser` y expone `/health` como healthcheck de imagen.

Los valores `infrawise_dev_only` son únicamente defaults locales y pueden reemplazarse con `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `DATABASE_URL`. No uses esos valores en producción ni publiques un archivo `.env`.

```bash
docker compose down       # detiene contenedores, conserva el volumen
docker compose down -v    # elimina también datos; operación destructiva
```

---

## CI

El workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) ejecuta en cada push a `main`/`master` y en cada pull request:

1. instala Python 3.12 y dependencias bloqueadas con `uv sync --extra dev --locked`;
2. ejecuta `ruff check .`;
3. verifica formato con `black --check .`;
4. ejecuta los 34 tests con cobertura de dominio, API, Mermaid e IA usando `AI_PROVIDER=template` para mantener CI offline;
5. compila los módulos Python;
6. valida `docker compose config --quiet`;
7. construye la imagen Docker etiquetada con el SHA del commit.

El workflow usa permisos mínimos de lectura, cache de uv y cancela ejecuciones obsoletas de la misma rama. El build de imagen se ejecuta en GitHub Actions, donde el daemon Docker del runner sí está disponible; en desarrollo local basta con ejecutar los mismos comandos de los quality gates.

---

## Estado del proyecto

**Fase 3 de 5 implementada.** El núcleo, la API y la capa de explicaciones están construidos, probados y documentados. La validación de `docker compose up` queda pendiente de ejecutar con Docker Desktop activo.

| Fase | Alcance | Estado |
| :--- | :--- | :--- |
| 0 — Esquema | `Requirements`, `CatalogService`, `ArchSpec`, catálogo AWS, golden fixture | ✅ Hecho |
| 1 — Rule Engine + Cost Engine | `recommend()` puro, determinista y testeado | ✅ Hecho — ver [`PHASE1_REPORT.md`](PHASE1_REPORT.md) |
| 2 — API + diagrama | FastAPI, persistencia, `ArchSpec` → Mermaid, Docker Compose | 🟡 Implementada — ver [`PHASE2_REPORT.md`](PHASE2_REPORT.md) |
| 3 — IA local | `AIExplainer`, Ollama opcional, fallback de templates y API integrada | 🟡 Implementada — ver [`PHASE3_REPORT.md`](PHASE3_REPORT.md) |
| 4 — Frontend | Next.js, formulario, diagrama interactivo, demo pública | ⬜ Pendiente |
| 5 — CI/CD + Terraform export | Quality gates CI implementados; `ArchSpec` → `.tf` pendiente | 🟡 CI inicial implementado |

> **Honestidad sobre "FinOps":** hoy no hay FinOps real. No hay ingesta de datos de consumo, ni rightsizing basado en métricas, ni forecasting. Lo que existe es un **estimador de costo declarativo** sobre precios de catálogo: la arquitectura se evalúa contra los requisitos que el usuario declara, no contra telemetría de producción. El término "FinOps" describe la dirección del proyecto, no lo que ya sabe hacer. Esto está también anotado en el [ROADMAP](ROADMAP.md#roadmap-v2--stretch--documentado-no-bloqueante).

**Módulos aún pendientes** — existen como marcadores de posición, no como funcionalidad:

```text
export/terraform.py · frontend/
```

---

## Configuración

El motor de reglas no lee variables de entorno ni archivos de configuración: **los requisitos son su única entrada**. Esto es deliberado, y es lo que hace que el dominio sea trivial de testear y reproducir. La API sí lee `DATABASE_URL` y las variables de Compose descritas abajo.

| Campo de `Requirements` | Tipo | Por defecto | Restricción |
| :--- | :--- | :--- | :--- |
| `app_type` | `web_api` · `web_app` · `static_site` · `background_worker` | — | — |
| `monthly_active_users` | `int` | — | `> 0` |
| `requests_per_minute` | `int` | — | `> 0` |
| `database` | `postgresql` · `mysql` · `none` | `postgresql` | — |
| `storage_gb` | `float` | — | `>= 0` |
| `availability` | `standard` · `high` · `critical` | `standard` | — |
| `monthly_budget_usd` | `float` | — | `> 0` |
| `region` | `str` | `us-east-1` | — |
| `optimize_for` | `cost` · `performance` · `availability` · `simplicity` · `balanced` | `balanced` | — |

La API usa estas variables de **entorno**. Cada una tiene un valor por defecto que permite desarrollo local sin configuración adicional:

| Variable | Fase | Por defecto | Propósito |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | 2 | `sqlite:///./infrawise.db` | SQLite local o PostgreSQL de arquitecturas guardadas |
| `POSTGRES_DB` | 2 | `infrawise` | Nombre de base en Compose |
| `POSTGRES_USER` | 2 | `infrawise` | Usuario de PostgreSQL en Compose |
| `POSTGRES_PASSWORD` | 2 | `infrawise_dev_only` | Credencial local; reemplazar en entornos reales |
| `AI_PROVIDER` | 3 | `ollama` | Selecciona el provider de explicaciones |

### Ajustar el catálogo

El catálogo es **datos, no código**. Para cambiar precios o agregar servicios, edita `examples/catalog.aws.sample.json` y regenera:

```bash
uv run python examples/_generate_examples.py
```

`base_monthly_usd` es **siempre un valor mensual**, incluso para precios por hora. Esa es la regla que impide que el motor mezcle tarifas horarias y mensuales por accidente. Para un servicio `instance_hour`, calcula `precio_por_hora * 730` y redondea a centavos.

Si agregas un servicio, el test dorado `test_matches_example_fixture` seguirá pasando mientras la selección no cambie; si cambia, actualiza `examples/architecture.example.json` a mano y confirma que el total sigue dentro del presupuesto.

---

## Documentación

| Archivo | Contenido |
| :--- | :--- |
| [`README.md`](README.md) | Este documento. |
| [`ROADMAP.md`](ROADMAP.md) | Fases 0–5 con milestones, tareas y definiciones de hecho. |
| [`PHASE1_REPORT.md`](PHASE1_REPORT.md) | Evidencia de la Fase 1: cambios, justificación, comandos ejecutados y pendientes. |
| [`PHASE2_REPORT.md`](PHASE2_REPORT.md) | Evidencia de la Fase 2: API, persistencia, Mermaid, Docker, pruebas y limitaciones. |
| [`PHASE3_REPORT.md`](PHASE3_REPORT.md) | Evidencia de la Fase 3: providers IA, contrato Ollama, fallback y API integrada. |
| [`schema/requirements.py`](schema/requirements.py) | La entrada del sistema y sus 4 enums. |
| [`schema/catalog.py`](schema/catalog.py) | `CatalogService`, `PricingModel`, `ComponentCategory`. |
| [`schema/architecture.py`](schema/architecture.py) | `ArchSpec` y sus 4 submodelos. |
| [`engine/cost_engine.py`](engine/cost_engine.py) | `estimate_cost()` y los 3 modelos de precio. |
| [`engine/rule_engine.py`](engine/rule_engine.py) | `filter_catalog()`, `pick_cheapest()`, `recommend()`. |
| [`api/main.py`](api/main.py) | Endpoints FastAPI, healthcheck y manejo de errores de dominio. |
| [`api/db.py`](api/db.py) | Engine SQLAlchemy, modelo `architectures` y sesiones. |
| [`diagram/mermaid.py`](diagram/mermaid.py) | Serialización pura de `ArchSpec` a Mermaid. |
| [`ai/base.py`](ai/base.py) · [`ai/factory.py`](ai/factory.py) | Contrato `AIExplainer`, selección de provider y fallback. |
| [`ai/ollama_provider.py`](ai/ollama_provider.py) · [`ai/template_provider.py`](ai/template_provider.py) | Provider Ollama validado y explicación determinista sin red. |
| [`Dockerfile`](Dockerfile) · [`docker-compose.yml`](docker-compose.yml) | Imagen API y PostgreSQL 16 con volumen/healthcheck. |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Quality gates y build de imagen en GitHub Actions. |
| [`tests/`](tests/) | La especificación ejecutable del dominio. |
| [`examples/`](examples/) | Catálogo, requisitos y golden fixture. |
| [`pyproject.toml`](pyproject.toml) | Dependencias y configuración de pytest, ruff y black. |

---

## Contacto

Si tienes alguna pregunta o feedback, ¡no dudes en escribirme!

- **Correo:** [gonzalezleyver6@gmail.com](mailto:gonzalezleyver6@gmail.com)
- **LinkedIn:** [Leyver Aaron Gonzalez Mendoza](https://www.linkedin.com/in/leyver-aaron-gonzalez-mendoza-7026a73a8/)

---

<div align="center">

**InfraWise**

*FinOps & Cloud Architecture Advisor*

`Python · Pydantic · FastAPI · SQLAlchemy · Docker · Mermaid · Ollama · Terraform`

*Fase 3 de 5 — explicaciones Ollama/template implementadas; Docker pendiente de validación local*

</div>
