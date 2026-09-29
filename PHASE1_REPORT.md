# Reporte de implementación — Fase 1

## 1. Resumen ejecutivo

Se completó la **Fase 1 — Rule Engine + Cost Engine** de InfraWise. El núcleo ahora puede transformar un objeto `Requirements` y un catálogo AWS en un `ArchSpec` reproducible, sin red, sin IA y sin efectos secundarios.

La fase quedó cerrada contra la definición de hecho del roadmap:

- cálculo de costos para `flat_monthly`, `instance_hour` y `per_unit`;
- filtrado por proveedor, categoría, disponibilidad y capacidad;
- selección de la opción técnicamente viable de menor costo;
- inclusión de componentes según las reglas del dominio;
- conexiones entre componentes;
- rechazo explícito de arquitecturas sin catálogo suficiente o fuera de presupuesto;
- `ScoreCard` explicable;
- pruebas unitarias, casos borde y prueba de propiedades sobre 50 entradas válidas.

## 2. Línea base y problemas encontrados

La inspección se realizó antes de editar la implementación.

| Verificación | Resultado inicial | Implicación |
|---|---|---|
| `pytest -q` | No ejecutable: `No module named pytest` | No había entorno reproducible ni dependencias de desarrollo declaradas. |
| `python -m compileall -q .` | Correcto | Los archivos Python existentes eran sintácticamente compilables, pero varios módulos estaban vacíos. |
| `docker compose config` | Falló con `empty compose file` | Docker Compose permanece fuera del alcance de esta fase; corresponde a la Fase 2. |
| Git | La carpeta no es un repositorio Git | No se puede entregar un diff o commit verificable. No se inicializó Git para no alterar el estado del usuario. |
| Implementación | `engine/`, `schema/catalog.py` y pruebas principales estaban vacíos | La Fase 1 requería construir el núcleo y sus pruebas, no solo refactorizarlo. |

## 3. Cambios realizados y justificación

### 3.1 Contrato de proyecto y reproducibilidad

- **`pyproject.toml`**
  - Se agregó el paquete `infrawise`, requisito de Python `>=3.11,<3.13` y dependencia de ejecución `pydantic`.
  - Se declararon dependencias de desarrollo: `pytest`, `pytest-cov`, `ruff` y `black`.
  - Se configuraron `pytest`, Ruff y Black con una longitud de línea común.
  - **Justificación:** un proyecto DevOps debe declarar cómo se instala, prueba y valida; así se evita depender del entorno global de cada desarrollador.

- **`uv.lock`**
  - Se generó y se validó con `uv lock --check`.
  - **Justificación:** fijar el grafo de dependencias reduce diferencias entre desarrollo, CI y futuros despliegues.

- **`.gitignore`**
  - Se excluyeron `.venv`, caches de pytest/Ruff, bytecode, cobertura, artefactos de build, configuración local y archivos `.env`.
  - **Justificación:** evita que artefactos generados, credenciales locales o estados del entorno entren al control de versiones.

### 3.2 Modelo de catálogo

- **`schema/catalog.py`**
  - Se implementaron `ComponentCategory`, `PricingModel` y `CatalogService` con Pydantic.
  - Se validan precios no negativos, capacidades positivas y precios unitarios opcionales.
  - **Justificación:** tipar el catálogo en el borde permite fallar temprano ante datos inválidos y mantiene separada la información de proveedores de la lógica de decisión.

- **`schema/architecture.py` y `schema/requirements.py`**
  - Se aplicaron ajustes de compatibilidad y estilo para Python 3.11: `StrEnum`, uniones con `|` y `datetime.UTC`.
  - **Justificación:** el código queda alineado con la versión declarada, evitando advertencias repetibles en los quality gates.

### 3.3 Cost Engine

- **`engine/cost_engine.py`**
  - Se implementó `estimate_cost(service, count=1, size_gb=None)`.
  - `FLAT_MONTHLY` e `INSTANCE_HOUR` utilizan el precio mensual normalizado del catálogo.
  - `PER_UNIT` exige `size_gb` y `unit_price_usd`.
  - `count <= 0`, modelos de precio desconocidos y entradas incompletas producen errores explícitos.
  - **Justificación:** un error de catálogo no debe convertirse silenciosamente en costo cero ni en un `TypeError` poco accionable. El resultado se redondea a centavos para mantener una salida estable.

### 3.4 Rule Engine

- **`engine/rule_engine.py`**
  - Se implementaron:
    - `filter_catalog(...)`;
    - `pick_cheapest(...)`;
    - `recommend(...)`;
    - `NoViableArchitecture`.
  - El filtrado usa AWS en v1, categoría, disponibilidad y límites de RPM/usuarios cuando el servicio los declara.
  - La disponibilidad usa una tabla ordenada (`standard < high < critical`), no comparaciones lexicográficas.
  - Para `HIGH`, compute se escala a dos instancias; storage/cache/CDN administrados pueden usarse con la garantía declarada por el catálogo; database y load balancer deben declarar `HIGH` explícitamente.
  - Las categorías se incluyen según el roadmap: compute siempre; database si se solicita; storage si `storage_gb > 0`; load balancer para alta disponibilidad o más de una instancia; cache para performance; CDN para sitios estáticos.
  - Se construyen conexiones con etiquetas `HTTP`, `reads/writes` y `cache`.
  - Se calcula `ScoreCard` con complejidad, margen de escalabilidad, disponibilidad y carga operativa.
  - Se genera un identificador estable a partir de requisitos y componentes. La selección es determinista; `created_at` continúa representando el momento en que se creó el snapshot.
  - **Justificación:** separar reglas puras de HTTP, IA y proveedores permite probar decisiones con rapidez, reproducir resultados y agregar la API en la Fase 2 sin reescribir el dominio.

- **Manejo de presupuesto**
  - El motor acumula el costo de cada opción mínima viable y lanza un error que identifica la categoría que rompe el presupuesto y el saldo disponible.
  - Nunca devuelve un `ArchSpec` que exceda `monthly_budget_usd`.
  - **Justificación:** el frontend y la futura API pueden convertir el error en una recomendación accionable, en vez de responder con una falla genérica.

### 3.5 Pruebas automatizadas

- **`tests/test_cost_engine.py`**
  - Cubre los tres modelos de precio, conteos inválidos, tamaño faltante y precio unitario ausente.

- **`tests/test_rule_engine.py`**
  - Verifica el fixture dorado contra `examples/architecture.example.json` comparando servicio, categoría y cantidad.
  - Cubre filtrado por capacidad/disponibilidad, selección barata, las seis categorías, conexiones, cache/CDN, presupuesto insuficiente y catálogo insuficiente para `CRITICAL`.
  - Ejecuta 50 combinaciones válidas reproducibles con semilla fija y comprueba que el resultado nunca supera el presupuesto; el único resultado alternativo permitido es `NoViableArchitecture`.
  - **Justificación:** las pruebas son una barrera de regresión y también una especificación ejecutable del dominio. La semilla fija evita pruebas inestables en CI.

- **TDD aplicado**
  - Primero se escribieron las pruebas y se ejecutaron en rojo por ausencia de `estimate_cost` y `recommend`.
  - Después se implementó el código mínimo, se ejecutó la suite en verde y finalmente se aplicaron formato y lint.
  - **Justificación:** se comprobó que las pruebas detectaban la funcionalidad faltante antes de aceptar la implementación.

### 3.6 Fixtures y roadmap

- **`examples/_generate_examples.py`**
  - Se corrigió el estilo y se hizo determinista el `created_at` del fixture generado.
  - **Justificación:** un generador que inserta la hora actual crea cambios espurios en cada ejecución y dificulta revisar artefactos en CI.

- **Fixtures en `examples/`**
  - Se regeneraron y se validaron con el generador; el total del ejemplo es `$107.51`, inferior al presupuesto de `$150`.

- **`ROADMAP.md`**
  - La Fase 1 se marcó como hecha y enlaza este reporte.
  - **Justificación:** mantener el roadmap sincronizado con el código evita que el estado del proyecto dependa de conocimiento informal.

## 4. Prácticas DevOps incorporadas

1. **Configuración como código:** dependencias, comandos de test y reglas de formato viven en `pyproject.toml`.
2. **Entorno reproducible:** `uv.lock` fija dependencias y `.venv` se mantiene fuera del proyecto versionable.
3. **Quality gates locales:** Ruff, Black, pytest, cobertura y compilación pueden ejecutarse de forma repetible.
4. **Fail fast:** validaciones de datos y presupuesto fallan con errores específicos antes de construir una arquitectura inválida.
5. **Pruebas de regresión:** el fixture dorado y el caso basado en 50 entradas protegen el contrato del motor.
6. **Separación de responsabilidades:** esquema, cálculo, reglas y pruebas están aislados; no se introdujo red ni SDK cloud en la fase pura.
7. **Seguridad básica de repositorio:** se excluyen `.env` y artefactos locales; no se copiaron secretos al reporte.
8. **Alcance controlado:** Docker Compose, API, persistencia, CI/CD, Terraform y frontend no se implementaron prematuramente; están definidos en fases posteriores del roadmap.

## 5. Evidencia de verificación final

Ejecutado desde `C:\Users\gonza\Desktop\InfraWise`:

```text
uv run --extra dev pytest --cov=engine --cov=schema --cov-report=term-missing -q
20 passed in 0.80s
TOTAL 241 statements, 96% coverage

uv run --extra dev ruff check .
All checks passed!

uv run --extra dev black --check .
21 files would be left unchanged.

uv lock --check
Resolved 22 packages in 1ms

uv run --extra dev python examples/_generate_examples.py
OK — total_monthly_cost_usd=107.51 (budget=150)
Wrote catalog.aws.sample.json, requirements.example.json, architecture.example.json

python -m compileall -q engine schema tests
exit code 0
```

## 6. Pendientes explícitos

- **Fase 2:** implementar API FastAPI, persistencia, Mermaid y Docker Compose. La validación inicial confirmó que el Compose actual está vacío; no se presentó como funcional.
- **Fase 3:** integrar Ollama con fallback de plantillas.
- **Fase 4:** construir frontend y despliegue público.
- **Fase 5:** agregar pipeline CI/CD completo y exportación Terraform.
- La carpeta no contiene un repositorio Git; por ello no se creó commit ni se reporta un diff Git.

## 7. Criterio de cierre

La Fase 1 se considera cerrada porque el motor de dominio corre localmente, sus decisiones son explicables y deterministas, los errores de datos/presupuesto son explícitos, las pruebas pasan y los quality gates definidos para esta fase están en verde.
