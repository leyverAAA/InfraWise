# Reporte de implementación — Fase 3

## 1. Resumen ejecutivo

Se implementó la **Fase 3 — IA local para las explicaciones** de InfraWise.

La arquitectura continúa siendo calculada exclusivamente por el Rule Engine. La IA solo redacta `Decision.reasoning`; no puede modificar `components`, `connections`, costos, cantidades ni factores.

La fase incorpora:

- Contrato `AIExplainer` mediante `Protocol`.
- Excepción explícita `AIProviderUnavailable`.
- Provider `OllamaExplainer` con endpoint local, timeout, temperatura baja y respuesta JSON validada.
- `TemplateExplainer` determinista en español y sin red.
- Factory con selección por `AI_PROVIDER` y healthcheck de Ollama.
- Fallback automático cuando Ollama está apagado, falla, responde JSON inválido o rompe el contrato.
- Integración en `POST /architectures`.
- Pruebas de contrato, prompt acotado, fallback y API.
- README y roadmap actualizados.

## 2. Línea base

Antes de modificar la Fase 3:

| Verificación | Resultado |
|---|---|
| Suite existente | `28 passed` |
| Ruff | Correcto |
| Black | Correcto |
| Compilación Python | Correcta |
| Docker Compose estático | Correcto |
| Ollama local | No instalado: `ollama: command not found` |

Al escribir primero las pruebas de Fase 3, la ejecución fue roja por el estado incompleto del paquete `ai`:

```text
ModuleNotFoundError: No module named 'ai.architecture'
```

`ai/__init__.py` contenía imports heredados hacia módulos inexistentes (`ai.architecture`, `ai.catalog` y `ai.requirements`). Se corrigió el inicializador para exponer el contrato y los providers reales de la Fase 3.

## 3. Cambios realizados y justificación

### 3.1 Contrato de provider

- **`ai/base.py`**
  - Se implementó `AIExplainer` como `Protocol`.
  - Se implementó `AIProviderUnavailable`.
  - El contrato define `explain(spec) -> list[Decision]`.
  - **Justificación:** agregar OpenAI, Gemini u otro provider en el futuro debe requerir una nueva clase, no modificar el Rule Engine ni la API.

- **`ai/__init__.py`**
  - Se eliminaron imports inválidos hacia módulos inexistentes.
  - Se exponen `AIExplainer`, `AIProviderUnavailable`, ambos providers y `get_explainer`.
  - **Justificación:** un paquete importable es un prerrequisito para que la API y los tests puedan cargar providers sin acoplamiento accidental a módulos que no existen.

### 3.2 Fallback determinista

- **`ai/template_provider.py`**
  - Se implementó `TemplateExplainer`.
  - Produce una decisión por componente.
  - Redacta razonamientos en español usando categoría, costo y factores calculados previamente.
  - No realiza llamadas de red.
  - Se agregó el alias `TemplateProvider` para compatibilidad semántica.
  - **Justificación:** una demo, CI o entorno sin Ollama debe continuar funcionando de forma reproducible. La ausencia de un modelo no puede convertirse en un `500`.

### 3.3 Provider Ollama

- **`ai/ollama_provider.py`**
  - Se implementó `OllamaExplainer`.
  - Valores por defecto:
    - `OLLAMA_URL=http://localhost:11434`;
    - `OLLAMA_MODEL=llama3.2`;
    - endpoint `/api/chat`;
    - timeout de 4 segundos, acotado a 3–5 segundos;
    - temperatura `0.2`;
    - `stream=false` y formato JSON.
  - Se agregó healthcheck mediante `/api/tags`.
  - Se capturan errores de red, timeout, JSON inválido y respuestas incompletas como `AIProviderUnavailable`.
  - Se agregó el alias `OllamaProvider`.
  - **Justificación:** el modelo local es opcional y debe fallar rápido. El timeout evita bloquear requests y el error específico permite que la API active el fallback.

### 3.4 Protección del contexto y contrato de salida

El prompt de Ollama recibe únicamente:

- `id` del componente;
- `service_id`;
- categoría;
- nombre visible;
- cantidad;
- costo mensual estimado;
- factores calculados por el Rule Engine.

No se envían `requirements`, `connections` ni datos ajenos a la explicación.

El system prompt ordena explícitamente:

- responder en español;
- devolver JSON;
- explicar solo los componentes recibidos;
- no sugerir ni mencionar servicios fuera de la lista;
- no modificar componentes, conexiones, costos ni cantidades.

La respuesta se valida con estas reglas:

- exactamente una decisión por componente;
- IDs en el mismo orden que los componentes;
- `reasoning` no vacío;
- factores originales conservados desde el Rule Engine.

**Justificación:** el modelo se usa como redactor, no como autoridad de arquitectura. Esta separación limita alucinaciones y mantiene la salida estructural bajo control determinista.

### 3.5 Factory y selección de provider

- **`ai/factory.py`**
  - `AI_PROVIDER=template` fuerza el fallback determinista.
  - `AI_PROVIDER=ollama` realiza healthcheck y usa Ollama solo si responde.
  - Un valor desconocido registra un warning y usa templates.
  - Si Ollama no está disponible, retorna `TemplateExplainer`.
  - **Justificación:** la configuración debe ser explícita, pero un provider opcional no debe convertirse en una dependencia dura de desarrollo o despliegue.

### 3.6 Integración en la API

- **`api/main.py`**
  - La versión de la API pasó a `0.3.0`.
  - `POST /architectures` genera primero el `ArchSpec` determinista y después agrega explicaciones.
  - Si el provider falla, se registra un warning y se usa `TemplateExplainer`.
  - Se valida también en la frontera de la API que el provider no haya devuelto una cantidad o secuencia de IDs incorrecta.
  - Solo se actualiza `decisions` mediante `model_copy`; `components` y `connections` permanecen intactos.
  - Las decisiones finales se persisten junto con el snapshot.
  - **Justificación:** la API mantiene una respuesta disponible aunque Ollama esté apagado o falle después del healthcheck inicial.

### 3.7 Pruebas

- **`tests/test_ai.py`**
  - Contrato de `TemplateExplainer`: una decisión por componente.
  - Factory con healthcheck de Ollama fallido.
  - Factory con provider template explícito.
  - Prompt de Ollama sin `requirements` ni `connections`.
  - Validación de respuesta Ollama con conjunto incorrecto de componentes.

- **`tests/test_api.py`**
  - Se fuerza `AI_PROVIDER=template` para que los tests sean offline y deterministas.
  - Se verifica que el POST devuelve una decisión por componente.
  - Se agrega una prueba de falla del provider con respuesta HTTP exitosa gracias al fallback.

- **TDD**
  - Las pruebas de Fase 3 se escribieron antes de los providers.
  - Se observó el fallo de colección esperado.
  - Se implementó el contrato mínimo, después Ollama, templates, factory e integración API.
  - **Justificación:** las pruebas definen el contrato antes de depender de detalles del endpoint o de un modelo específico.

## 4. Configuración

Variables opcionales:

```bash
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT_SECONDS=4
```

Recomendaciones de uso:

```bash
# CI, tests y demos sin red
AI_PROVIDER=template

# Desarrollo con Ollama
ollama serve
ollama pull llama3.2
AI_PROVIDER=ollama
```

No se agregaron credenciales ni tokens. Ollama local no requiere una API key para este flujo.

## 5. Evidencia de verificación

```text
uv run --extra dev ruff check .
All checks passed!

uv run --extra dev black --check .
26 files left unchanged.

uv run --extra dev pytest --cov=engine --cov=api --cov=diagram --cov=schema --cov=ai --cov-report=term-missing -q
34 passed in 2.03s
TOTAL 472 statements, 91% coverage

uv lock --check
Resolved 42 packages in 1ms

python -m compileall -q .
exit code 0

docker compose config --quiet
exit code 0
```

### Smoke test sin Ollama

Se ejecutó un POST real mediante `TestClient` con `AI_PROVIDER` sin definir y Ollama ausente:

```text
Ollama is unavailable; using template explanations
status 201 decisions 4
```

Esto verifica el criterio principal de resiliencia: la request no falla cuando el provider local no está disponible.

### Limitación externa

No se ejecutó una generación real con Ollama porque el comando no está instalado en el entorno actual. Por lo tanto, quedan sin verificar localmente la calidad semántica del modelo y la respuesta de un servidor Ollama real. El contrato HTTP, la validación de JSON, el timeout y el fallback sí están cubiertos con pruebas controladas.

## 6. Estado del roadmap

La Fase 3 queda **implementada en código, pruebas y API**, con Ollama como integración opcional y templates como fallback operativo.

Pendientes posteriores:

- Fase 4: frontend y demo pública.
- Fase 5: exportación Terraform y ampliación del pipeline.
- Validar el provider real con `ollama serve` y `ollama pull llama3.2`.
- Medir calidad de las explicaciones con ejemplos y criterios de evaluación semántica; las pruebas actuales validan estructura y seguridad del contrato, no calidad subjetiva.

No se creó commit ni se modificó el estado remoto del repositorio.
