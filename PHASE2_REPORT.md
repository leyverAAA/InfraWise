# Reporte de implementación — Fase 2

## 1. Resumen ejecutivo

Se implementó la Fase 2 — **API + diagrama** de InfraWise. La aplicación ahora expone el Rule Engine por HTTP, persiste `ArchSpec` completos y puede convertirlos en diagramas Mermaid.

La implementación cubre:

- `POST /architectures` con validación Pydantic y respuesta `201`.
- `GET /architectures/{id}` con respuesta `404` cuando no existe.
- `GET /architectures/{id}/diagram` como `text/plain`.
- Persistencia mínima con SQLAlchemy en la tabla `architectures`.
- SQLite para desarrollo local y PostgreSQL 16 para Compose.
- Documentación OpenAPI/Swagger en `/docs`.
- Dockerfile ejecutable con Python 3.12 y usuario no root.
- Docker Compose con API, PostgreSQL, healthcheck y volumen persistente.
- Pruebas de API, persistencia y serialización Mermaid.

La parte de código y configuración quedó implementada y validada estáticamente. La ejecución real de Docker quedó pendiente porque el daemon de Docker Desktop no estaba disponible en el entorno.

## 2. Línea base

Antes de los cambios se ejecutó la suite de Fase 1 y los quality gates existentes.

| Verificación | Resultado inicial |
|---|---|
| `uv run --extra dev pytest -q` | `20 passed` |
| Ruff | Correcto |
| Black | Correcto |
| `uv lock --check` | Correcto |
| `python -m compileall -q .` | Correcto |
| `docker compose config` | Falló con `empty compose file` |
| Dependencias FastAPI/SQLAlchemy/httpx | No instaladas |
| Docker daemon | No disponible: pipe `dockerDesktopLinuxEngine` inexistente |

Para respetar TDD, primero se agregaron las pruebas de Fase 2 y se ejecutaron en rojo por la ausencia de `api.db` y `to_mermaid`:

```text
ModuleNotFoundError: No module named 'api.db'
ImportError: cannot import name 'to_mermaid'
```

Después se implementó la funcionalidad y las pruebas pasaron.

## 3. Cambios realizados y justificación

### 3.1 Dependencias y reproducibilidad

- **`pyproject.toml`**
  - Se agregaron FastAPI, Uvicorn, SQLAlchemy y `psycopg[binary]` como dependencias de ejecución.
  - Se agregaron `httpx` y una versión compatible de `anyio` para `TestClient`.
  - FastAPI se acotó a `>=0.115,<0.120` para mantener una combinación estable con Starlette y evitar advertencias del cliente de pruebas.
  - **Justificación DevOps:** las dependencias de API, base de datos y pruebas deben estar declaradas en el proyecto, no instaladas manualmente en cada máquina.

- **`uv.lock`**
  - Se regeneró y se validó con `uv lock --check`.
  - **Justificación:** el entorno local y el futuro CI deben resolver el mismo grafo de dependencias.

### 3.2 Persistencia

- **`api/db.py`**
  - Se implementó el engine configurable mediante `DATABASE_URL`.
  - Se usa SQLite por defecto para desarrollo local.
  - Se usa `JSONB` en PostgreSQL y una variante `JSON` en SQLite.
  - Se implementó la tabla `architectures` con:
    - `id TEXT PRIMARY KEY`;
    - `payload JSON/JSONB`;
    - `created_at TIMESTAMP`.
  - Se implementaron `Base`, `ArchitectureRecord`, `init_db()` y la dependencia `get_db()`.
  - **Justificación:** almacenar el `ArchSpec` completo como snapshot mantiene la persistencia simple y conserva la trazabilidad de la recomendación sin normalizar prematuramente el modelo de dominio.

- La sesión se cierra mediante una dependencia de FastAPI por request.
  - **Justificación:** evita conexiones abiertas y hace explícito el ciclo de vida de recursos.

### 3.3 API HTTP

- **`api/main.py`**
  - Se añadió una aplicación FastAPI con versión `0.2.0`.
  - El catálogo de ejemplo se carga desde `examples/catalog.aws.sample.json`.
  - `POST /architectures`:
    - recibe `Requirements`;
    - ejecuta `recommend()`;
    - devuelve `422` con el mensaje de `NoViableArchitecture`;
    - persiste el snapshot;
    - devuelve `201` y el `ArchSpec` completo.
  - Se implementó actualización idempotente cuando la misma recomendación estable se publica nuevamente.
  - `GET /architectures/{id}` recupera el snapshot o devuelve `404`.
  - `GET /architectures/{id}/diagram` devuelve Mermaid como texto plano.
  - Se añadió `GET /health` para healthchecks del contenedor.
  - **Justificación:** separar el transporte HTTP del Rule Engine permite reutilizar las reglas, probarlas sin red y exponer errores de dominio de forma útil al consumidor.

- **Documentación automática**
  - FastAPI expone `/docs` y `/openapi.json`.
  - **Justificación:** OpenAPI reduce ambigüedad entre backend, frontend y pruebas de integración.

### 3.4 Diagrama Mermaid

- **`diagram/mermaid.py`**
  - Se implementó `to_mermaid(spec)` como función pura.
  - Cada componente se representa como nodo.
  - Cada conexión se representa como flecha con etiqueta cuando existe.
  - Se escapan comillas, barras invertidas y saltos de línea en nombres y etiquetas.
  - **Justificación:** una función pura es fácil de probar, no requiere base de datos y evita acoplar la representación visual a FastAPI.

### 3.5 Docker y Compose

- **`Dockerfile`**
  - Usa `python:3.12-slim`.
  - Instala el paquete con `pip install --no-cache-dir .`.
  - Expone el puerto `8000`.
  - Ejecuta Uvicorn mediante el comando definido en la imagen.
  - Ejecuta como usuario no root `appuser`.
  - Incluye `HEALTHCHECK` contra `/health`.
  - **Justificación DevOps:** imagen pequeña, proceso reproducible, menor privilegio y healthcheck para que el orquestador conozca el estado de la aplicación.

- **`docker-compose.yml`**
  - Servicio `api` construido desde el Dockerfile.
  - Servicio `db` basado en `postgres:16`.
  - `DATABASE_URL` se comparte mediante variables de Compose.
  - `api` espera a que PostgreSQL esté saludable.
  - Se agregó el volumen nombrado `postgres_data`.
  - Se configuró `restart: unless-stopped`.
  - La contraseña por defecto está marcada como `infrawise_dev_only` y debe sustituirse mediante `.env` en un entorno real.
  - **Justificación:** la aplicación y su dependencia principal arrancan con una topología declarativa, conservando los datos de PostgreSQL entre reinicios.

- **`.dockerignore`**
  - Excluye entornos virtuales, caches, reportes locales, `.env`, secretos, llaves privadas, `known_hosts`, bytecode y metadata de Git.
  - **Justificación de seguridad:** al usar `COPY . .`, los secretos y artefactos locales no deben entrar al contexto ni a las capas de la imagen.

- **`.gitignore`**
  - Se añadieron patrones para secretos, llaves privadas y bases SQLite locales.

### 3.6 Pruebas

- **`tests/test_api.py`**
  - Prueba POST exitoso con persistencia y posterior GET.
  - Prueba `422` para presupuesto insuficiente.
  - Prueba `422` para validación Pydantic.
  - Prueba `404` para arquitectura inexistente.
  - Prueba endpoint de diagrama y tipo MIME `text/plain`.
  - Prueba `404` para diagrama inexistente.
  - Usa SQLite en memoria con `StaticPool`, sin depender de Docker.
  - **Justificación:** la API se verifica de forma rápida y determinista en CI, mientras PostgreSQL queda cubierto por la configuración de Compose.

- **`tests/test_diagram.py`**
  - Verifica encabezado Mermaid, nodos, conexiones y escaping de etiquetas.

## 4. Evidencia de verificación

### Suite y calidad

```text
uv run --extra dev pytest --cov=engine --cov=api --cov=diagram --cov=schema --cov-report=term-missing -q
28 passed in 8.26s
TOTAL 334 statements, 94% coverage

uv run --extra dev ruff check .
All checks passed!

uv run --extra dev black --check .
24 files would be left unchanged.

uv lock --check
Correcto

python -m compileall -q .
exit code 0

uv build
Successfully built dist/infrawise-0.1.0.tar.gz
Successfully built dist/infrawise-0.1.0-py3-none-any.whl
```

### Configuración Compose

```text
docker compose config --quiet
exit code 0
```

La configuración expandida confirmó:

- API en el puerto `8000`.
- PostgreSQL 16.
- `DATABASE_URL` apuntando al servicio `db`.
- dependencia con `condition: service_healthy`.
- volumen `infrawise_postgres_data`.

### Prueba local HTTP

Con Uvicorn ejecutándose localmente y SQLite como persistencia:

```text
GET /health                         -> 200
POST /architectures                 -> 201
GET /architectures/{id}/diagram     -> 200, comienza con graph TD
GET /docs                           -> 200
GET /openapi.json                   -> 200
```

### Limitación externa

`docker build -t infrawise:phase2 .` no pudo ejecutarse porque Docker Desktop no tenía el daemon disponible:

```text
error during connect: open //./pipe/dockerDesktopLinuxEngine:
The system cannot find the file specified.
```

Por la misma razón no se ejecutó `docker compose up` con PostgreSQL real. La configuración fue validada con `docker compose config --quiet`, la imagen fue validada mediante `uv build` y la API fue ejercitada localmente con SQLite.

## 5. Estado del roadmap

La Fase 2 queda **implementada en código y configuración**. La única verificación pendiente es ejecutar Docker Desktop y validar el flujo completo con PostgreSQL real:

```bash
docker compose up --build
curl http://localhost:8000/health
```

La Fase 3 — integración de IA local con Ollama — permanece fuera del alcance.

No se creó commit porque la carpeta no contiene un repositorio Git.
