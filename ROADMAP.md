# Roadmap — InfraWise

Cada fase termina en algo que corre, nunca en código a medias. Si el
tiempo aprieta, el corte es al final de una fase completa — no a la
mitad de una tarea.

Cómo usarlo: cada `-[ ]` de segundo nivel es del tamaño de un issue de
GitHub. Cada fase es un milestone. Si usas GitHub Projects, un board
con columnas `Backlog / En progreso / Hecho` y una etiqueta por fase
alcanza y sobra.

| Fase | Milestone | Bloquea a | Esfuerzo aprox.* |
|---|---|---|---|
| 0 — Esquema | — | todas | hecho |
| 1 — Rule Engine + Cost Engine | `v0.1` | 2, 3, 5 | 5–8 h |
| 2 — API + diagrama | `v0.2` | 3, 4 | 6–9 h |
| 3 — IA local (Ollama) | `v0.3` | 4 | 4–6 h |
| 4 — Frontend + demo pública | `v0.4` | — | 6–10 h |
| 5 — CI/CD + Terraform export | `v1.0` | — | 5–8 h |

\* Asumiendo que ya conoces el stack (FastAPI, pytest, Docker). Son
sesiones, no jornadas completas — repártelo en 2–3 sentadas por fase.

---

## Fase 0 — Esquema *(hecho)*

`Requirements`, `CatalogService`, `ArchSpec` en Pydantic + catálogo AWS
de 11 servicios + un `ArchSpec` de ejemplo verificado a mano
($107.51/mes, bajo presupuesto de $150). Ver `schema/` y `examples/`.

---

## Fase 1 — Rule Engine + Cost Engine *(hecha)*

**Resultado verificado:** `recommend(requirements, catalog) -> ArchSpec` funciona sin red ni IA, con selección determinista, validación de presupuesto, scoring, conexiones y tests automatizados. El detalle de cambios, decisiones y evidencia está en [`PHASE1_REPORT.md`](PHASE1_REPORT.md).

**Objetivo:** `recommend(requirements, catalog) -> ArchSpec` puro — sin
red, sin IA, 100% determinista y testeable con `assert`.

**Milestone `v0.1`** — Definición de hecho: `pytest tests/test_rule_engine.py
tests/test_cost_engine.py` en verde, y cada rama de categoría (compute,
database, storage, load_balancer, cache, cdn) tocada por al menos un test.

### 1.1 `engine/cost_engine.py`

```python
def estimate_cost(service: CatalogService, count: int = 1, size_gb: float | None = None) -> float:
    ...
```

- `FLAT_MONTHLY` → `base_monthly_usd * count`
- `INSTANCE_HOUR` → `base_monthly_usd` ya viene pre-convertido a mensual en el catálogo (ver `catalog.aws.sample.json`) → `base_monthly_usd * count`
- `PER_UNIT` → `unit_price_usd * size_gb`
- Casos borde a cubrir con test:
  - `PER_UNIT` sin `size_gb` → `ValueError` explícito, no `None * float`
  - `count <= 0` → `ValueError`
  - `unit_price_usd is None` en un servicio `PER_UNIT` → error de datos del catálogo, no debe fallar en silencio
- Es literalmente la función `cost_of()` ya prototipada en `examples/_generate_examples.py` — muévela, no la reescribas.

### 1.2 `engine/rule_engine.py` — selección por categoría

```python
def filter_catalog(catalog: list[CatalogService], category: ComponentCategory, req: Requirements) -> list[CatalogService]: ...
def pick_cheapest(candidates: list[CatalogService], count: int = 1) -> CatalogService: ...
def recommend(req: Requirements, catalog: list[CatalogService]) -> ArchSpec: ...
```

Reglas de filtrado (`filter_catalog`):
- `provider == "aws"` (hardcodeado en v1, a propósito)
- `category` coincide
- `min_availability` del servicio es compatible con `req.availability` (standard < high < critical — define este orden en una tabla, no en una cadena de `if`)
- `max_rpm >= req.requests_per_minute` y `max_users >= req.monthly_active_users`, cuando el servicio declara esos límites (algunos, como S3 o ALB, no aplican)

Reglas de inclusión de categoría (cuáles componentes entran al `ArchSpec`):
| Categoría | Se incluye cuando |
|---|---|
| `compute` | siempre |
| `database` | `req.database != DatabaseEngine.NONE` |
| `storage` | `req.storage_gb > 0` |
| `load_balancer` | `req.availability != AvailabilityTier.STANDARD` **o** el compute elegido necesita `count > 1` |
| `cache` | `req.optimize_for == OptimizeFor.PERFORMANCE` |
| `cdn` | `req.app_type == AppType.STATIC_SITE` |

Reglas de `count` en compute:
- `availability == STANDARD` → `count = 1`
- `availability in (HIGH, CRITICAL)` → `count = 2` como mínimo (evita punto único de falla — es la misma lógica que usamos a mano en `architecture.example.json`)

### 1.3 Conexiones (`connections`)

Construir según qué categorías terminaron presentes:
- Si hay `load_balancer` → `load_balancer -> compute` (label `"HTTP"`); si no, no hay conexión entrante explícita (el compute es el punto de entrada)
- `compute -> database` (label `"reads/writes"`), si hay database
- `compute -> storage` (label `"reads/writes"`), si hay storage
- `compute -> cache` (label `"cache"`), si hay cache
- `cdn -> compute` o `cdn -> storage` según `app_type` (static → storage; si no, → compute)

### 1.4 Manejo de "no alcanza"

```python
class NoViableArchitecture(Exception):
    """No hay combinación de catálogo que cumpla los requisitos dentro del presupuesto."""
```

- Se lanza cuando, tras elegir la opción **más barata que técnicamente cumple** en cada categoría obligatoria, la suma ya excede `monthly_budget_usd`.
- El mensaje de error debe decir *qué categoría* rompió el presupuesto y por cuánto (ej. `"database mínimo viable cuesta $60, pero solo quedan $40 de presupuesto tras compute+storage"`) — esto es lo que después reusa el frontend para decirle al usuario "sube tu presupuesto a $X" en vez de solo fallar.
- **Nunca** se debe devolver un `ArchSpec` que exceda el presupuesto sin avisar.

### 1.5 Scoring (`ScoreCard`)

Heurísticas simples y documentadas (no hace falta que sean sofisticadas, sí que sean explicables):
- `complexity`: `LOW` si ≤2 categorías presentes, `MEDIUM` si 3–4, `HIGH` si 5+
- `scalability`: `HIGH` si el compute elegido tiene ≥2x de margen entre `max_rpm` y `req.requests_per_minute`; si no, `MEDIUM`
- `operational_overhead`: `LOW` si todo es managed (RDS, no EC2 corriendo Postgres a mano); sube a `MEDIUM`/`HIGH` según cuántos componentes requieren mantenimiento manual (en v1, con solo EC2/RDS/S3/ALB/ElastiCache/CloudFront, esto puede ser casi siempre `LOW`/`MEDIUM` — está bien, documenta el criterio para cuando el catálogo crezca)

### 1.6 Tests

- **Test dorado** (`tests/test_rule_engine.py::test_matches_example_fixture`): cargar `requirements.example.json` + `catalog.aws.sample.json`, correr `recommend()`, comparar contra `architecture.example.json` — compara `{service_id, category, count}` por componente, **no** los costos exactos (esos pueden moverse si ajustas precios del catálogo).
- **Property test** (`tests/test_rule_engine.py::test_never_exceeds_budget`): generar ~50 `Requirements` aleatorios pero válidos (rangos razonables de usuarios/rpm/budget), y por cada uno: o `recommend()` devuelve un `ArchSpec` con `total_monthly_cost_usd <= monthly_budget_usd`, o lanza `NoViableArchitecture`. Nunca un tercer resultado.
- **Test de borde** (`test_budget_too_low_raises`): `monthly_budget_usd=1` → debe lanzar `NoViableArchitecture`, no un `ArchSpec` roto.
- **Test de borde** (`test_critical_availability`): `availability=CRITICAL` con el catálogo actual (que solo llega a `min_availability="high"`) → debe lanzar un error claro de "catálogo insuficiente", no fallar con un `KeyError` genérico.

---

## Fase 2 — API + diagrama

**Objetivo:** exponer el Rule Engine por HTTP y convertir un `ArchSpec`
en un diagrama que un humano pueda leer sin abrir el JSON.

**Milestone `v0.2`** — Definición de hecho: `docker compose up` levanta
API + Postgres con un comando; `curl -X POST` contra `/architectures`
devuelve un `ArchSpec` completo; `/docs` de FastAPI funciona.

### 2.1 `api/main.py`
- `POST /architectures` — body: `Requirements` (JSON) → valida con Pydantic automáticamente → llama `rule_engine.recommend()` → si lanza `NoViableArchitecture`, responder `422` con el mensaje explicativo de la sección 1.4 (no un 500 genérico) → si tiene éxito, persistir y devolver `ArchSpec` con `201`
- `GET /architectures/{id}` — `404` si no existe
- `GET /architectures/{id}/diagram` — `text/plain`, devuelve el bloque Mermaid

### 2.2 Persistencia mínima
- Tabla `architectures(id TEXT PK, payload JSONB, created_at TIMESTAMPTZ)` vía SQLAlchemy — guardas el `ArchSpec.model_dump(mode="json")` completo en `payload`, no lo normalizas en columnas. No necesitas más que esto en v1: el `ArchSpec` ya es tu modelo de datos.
- `db.py`: engine + sesión; usa la misma variable `DATABASE_URL` que el `docker-compose.yml` de la sección 2.4.

### 2.3 `diagram/mermaid.py`

```python
def to_mermaid(spec: ArchSpec) -> str: ...
```

- Función pura: recibe un `ArchSpec`, no toca la base de datos ni hace I/O.
- Cada `Component` → un nodo `id[display_name]`; cada `Connection` → una flecha `source -->|label| target`.
- Test: el resultado debe empezar con `graph TD` (o `flowchart TD`) y contener el `id` de cada componente del spec — no hace falta comparar el string completo, eso hace el test frágil ante cambios de formato.

### 2.4 `Dockerfile` + `docker-compose.yml`
- `Dockerfile`: imagen `python:3.12-slim`, instala dependencias (Poetry o `pip install -e .`), expone `8000`, `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0"]`
- `docker-compose.yml`: servicio `api` (build `.`, depende de `db`), servicio `db` (`postgres:16`, volumen nombrado para no perder datos entre reinicios), variable `DATABASE_URL` compartida
- Prueba manual de aceptación: clonar el repo en limpio, `docker compose up`, y sin ningún paso manual adicional poder pegar un `curl` contra `localhost:8000/architectures`

### 2.5 Tests
- `tests/test_api.py` con `TestClient` de FastAPI (no necesitas Docker corriendo para estos, usa SQLite en memoria o un mock de la sesión)
- Caso feliz: `POST /architectures` con el `requirements.example.json` → `201` + JSON con `components`
- Caso de error: `monthly_budget_usd` absurdamente bajo → `422`
- `GET` de un id inexistente → `404`

---

## Fase 3 — IA local para las explicaciones

**Objetivo:** llenar `decisions[]` en español, usando Ollama — sin que
la IA toque nunca `components` ni `connections`.

**Milestone `v0.3`** — Definición de hecho: con `ollama serve` corriendo
y un modelo descargado, la respuesta de `POST /architectures` trae
`decisions` redactadas por el modelo; apagando Ollama, la misma request
sigue funcionando (con el fallback), sin 500 ni timeout eterno.

### 3.1 `ai/base.py`

```python
class AIExplainer(Protocol):
    def explain(self, spec: ArchSpec) -> list[Decision]: ...
```

Documenta en el docstring que esta interfaz es intencional: aunque v1
solo implemente un provider, es lo que hace que "agregar OpenAI/Gemini
después" sea una clase nueva, no una reescritura.

### 3.2 `ai/ollama_provider.py`
- Llama al endpoint local de Ollama (`http://localhost:11434/api/chat` o `/api/generate`) con un modelo chico (`llama3.2` o `qwen2.5:7b` — ambos corren bien en una laptop sin GPU dedicada)
- El prompt recibe **solo** el `ArchSpec` ya armado: `components` + `factors` de cada `Decision` parcial que ya calculó el Rule Engine (sección 1.5). El system prompt debe decir explícitamente: *"Explica por qué se eligió cada componente usando SOLO los factores dados. No sugieras ni menciones servicios que no estén en la lista."*
- `temperature` baja (0.2–0.3) — esto es redacción, no creatividad
- Timeout corto (3–5s) y manejo explícito de `ConnectionError`/timeout → lanzar `AIProviderUnavailable` (no dejar que reviente como excepción genérica)

### 3.3 `ai/template_provider.py`
- Implementa la misma interfaz, sin red: rellena `reasoning` con plantillas de texto parametrizadas por los `factors` (los mismos que escribimos a mano en `architecture.example.json` son buen punto de partida para las plantillas)
- Esto es lo que garantiza que una demo en vivo nunca se caiga por un Ollama que no arrancó a tiempo

### 3.4 `ai/factory.py`
```python
def get_explainer() -> AIExplainer: ...
```
- Lee `AI_PROVIDER` de entorno (`ollama` por default)
- Hace un *health check* rápido contra Ollama antes de comprometerse; si falla, regresa `TemplateExplainer` y loggea un warning — la request del usuario nunca debe fallar por esto

### 3.5 Tests
- Mockear `ollama_provider` lanzando `AIProviderUnavailable` → confirmar que `factory` cae a `TemplateExplainer` y la respuesta igual trae `decisions` no vacías
- Test de contrato: para cualquier `ArchSpec` de entrada, `len(explain(spec)) == len(spec.components)` (una `Decision` por componente, ni más ni menos) — este test debe pasar con **ambos** providers

---

## Fase 4 — Frontend + demo pública

**Objetivo:** que cualquiera con un link pueda usar la herramienta sin
clonar el repo.

**Milestone `v0.4`** — Definición de hecho: link público, formulario
funcional, diagrama y explicaciones visibles, capturas o GIF en el
`README`.

### 4.1 Formulario
- Un campo por cada campo de `Requirements` (usa los mismos `enum` como `<select>`, así el frontend nunca manda un valor que el backend rechace)
- Validación en cliente que espeje las restricciones de Pydantic (`gt=0`, etc.) — no es obligatorio pero evita round-trips de error innecesarios

### 4.2 Vista de resultado
- Diagrama: renderizar el string Mermoid que devuelve `/diagram` (librería `mermaid` de npm, o el CDN de Mermaid)
- Tabla de costos: una fila por `Component`, columna de `estimated_monthly_cost_usd`, fila de total
- `ScoreCard`: los 5 valores como badges o chips
- `decisions`: lista de texto, una por componente

### 4.3 Deploy
- Backend: Railway, Render o Fly.io (cualquiera con soporte a Docker Compose o al menos Dockerfile + Postgres administrado)
- Frontend: Vercel o Netlify
- `CORS` en `api/main.py` debe permitir explícitamente el dominio del frontend desplegado (no `allow_origins=["*"]` en producción — es un detalle chico que en una entrevista de DevOps sí se nota)
- Link final documentado en el `README`, con una captura o GIF corto del flujo completo

---

## Fase 5 — CI/CD + Terraform export

**Objetivo:** demostrar el pedazo más "DevOps" del proyecto — no solo
que la app funciona, sino que se construye, prueba y despliega sola.

**Milestone `v1.0`** — Definición de hecho: badge de CI en verde en el
`README`; `to_terraform()` produce archivos `.tf` que pasan
`terraform validate`.

### 5.1 `.github/workflows/ci.yml`
Pasos, en orden (que cada uno falle rápido si algo está mal, antes de gastar tiempo en el siguiente):
1. `actions/checkout`
2. `actions/setup-python` (misma versión que el `Dockerfile`)
3. Instalar dependencias
4. `ruff check .` y `black --check .`
5. `pytest --cov=engine --cov=ai --cov=diagram`
6. `docker build .` (solo construir, no publicar, salvo que quieras agregar push a GHCR en tags)

### 5.2 `export/terraform.py`

```python
def to_terraform(spec: ArchSpec) -> dict[str, str]: ...
```
- Un archivo por tipo de recurso presente en el spec: `ec2.tf`, `rds.tf`, `s3.tf`, `alb.tf` — **no** intentes cubrir todo el catálogo de una vez, arranca con estos cuatro que son los que aparecen en el ejemplo dorado
- Cada función `_ec2_block(component) -> str`, `_rds_block(component) -> str`, etc., mapea `Component.config` a los argumentos del recurso Terraform correspondiente (instance type, engine, multi_az, count vía `count = N`)
- Escribir a disco: `export/writer.py::write_terraform_files(spec, out_dir)`

### 5.3 Validación
- Si tienes el binario de `terraform` disponible: agregar un test o paso de CI que corra `terraform validate` sobre el output — si añadir el binario a CI es demasiado esfuerzo para el tiempo que tienes, está bien dejarlo como paso manual documentado en el `README` ("corre esto para validar") y priorizar el resto del roadmap
- Bonus para la entrevista: usar el propio Terraform generado por tu herramienta para desplegar la demo de la Fase 4 — es la línea que cierra la historia ("la herramienta se despliega a sí misma")

---

## Roadmap v2 / stretch — documentado, no bloqueante

No lo construyas ahora. Ponlo en el `README` como "próximos pasos" —
priorizar un scope y decirlo explícitamente también es una señal de
seniority, aunque sea para un puesto jr.

- [ ] Soporte GCP — el catálogo (`CatalogService`) ya está diseñado para esto: es agregar filas de datos, no reescribir el Rule Engine
- [ ] "Optimizar por" real: generar 2–3 `ArchSpec` con distintos `optimize_for` para el mismo `Requirements` y compararlos lado a lado en la UI
- [ ] Providers de IA adicionales (OpenAI/Gemini) detrás de la misma interfaz `ai/base.py`
- [ ] FinOps con datos reales de uso (CloudWatch u otra fuente de métricas). Sin esto, cualquier "rightsizing" es heurístico sobre los mismos inputs declarados, no FinOps real — decláralo así en el README para no sobre-vender el término