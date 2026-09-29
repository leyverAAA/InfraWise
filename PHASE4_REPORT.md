# Reporte de implementación — Fase 4

## 1. Resumen ejecutivo

Se implementó la **Fase 4 — Frontend + demo pública** de InfraWise.

La aplicación ahora cuenta con una interfaz Next.js funcional que consume la API de Fase 2 y presenta el resultado de Fase 3 en una experiencia usable:

- formulario para los nueve campos de `Requirements`;
- validación cliente alineada con Pydantic;
- generación de arquitecturas vía `POST /architectures`;
- renderizado Mermaid desde `/architectures/{id}/diagram`;
- desglose de costos por componente;
- `ScoreCard`;
- decisiones explicadas por Ollama o por el fallback determinista;
- manejo de errores de API y presupuesto;
- diseño responsive para escritorio y móvil;
- CORS explícito entre frontend y backend;
- quality gates de frontend: lint, TypeScript y build de producción.

El despliegue público no se realizó porque requiere seleccionar un proveedor y configurar credenciales/dominios externos. La fase queda implementada y localmente verificable.

## 2. Línea base

Antes de los cambios:

| Verificación | Resultado |
|---|---|
| Backend | `34 passed` |
| Ruff / Black | Correctos |
| Frontend | `frontend/README.md` vacío; no existía aplicación Next.js |
| Node.js | `v22.23.2` |
| npm | `10.9.8` |
| Docker Compose | Configuración existente, sin frontend asociado |

## 3. Cambios realizados y justificación

### 3.1 Aplicación Next.js

Se creó la aplicación en `frontend/` con:

- **`package.json`**
  - Next.js `16.3.6`;
  - React `19.3.0`;
  - Mermaid `12.0.0`;
  - TypeScript `5.9.3`;
  - ESLint `9.39.5` y `eslint-config-next`.
- **`package-lock.json`**
  - Dependencias reproducibles para npm.
- **`next.config.ts`**
  - Configura explícitamente la raíz de Turbopack en `frontend/`.
- **`tsconfig.json`**, `next-env.d.ts` y `eslint.config.mjs`.
- **`frontend/.gitignore`**
  - Excluye `node_modules`, `.next`, `out`, `*.tsbuildinfo` y variables locales.

**Justificación DevOps:** el frontend tiene su propio manifiesto, lockfile, scripts de validación y exclusiones de artefactos. Esto permite construirlo de forma independiente y reproducible en CI o en un proveedor como Vercel/Netlify.

### 3.2 Contrato TypeScript y validación

- **`frontend/lib/types.ts`**
  - Replica el contrato de `Requirements`, `ArchSpec`, `Component`, `Connection`, `Decision` y `ScoreCard`.
  - **Justificación:** el frontend no usa objetos sin tipo ni vuelve a inventar los nombres de campos; comparte el contrato conceptual de la API.

- **`frontend/lib/validation.ts`**
  - Implementa `DEFAULT_REQUIREMENTS` basado en el fixture del proyecto.
  - Valida usuarios, RPM, storage, presupuesto y región antes del request.
  - **Justificación:** evita round-trips innecesarios y ofrece feedback inmediato, sin reemplazar la validación autoritativa del backend.

### 3.3 Experiencia de usuario

- **`frontend/app/page.tsx`**
  - Formulario con selects para los enums del backend.
  - Campos numéricos con límites HTML y validación adicional.
  - Estado de carga durante la generación.
  - Manejo de errores `422`, errores de red y respuestas incompletas.
  - Consulta posterior del endpoint Mermaid.
  - Tabla de costos, total y margen de presupuesto.
  - ScoreCard visual.
  - Lista de decisiones explicadas por componente.
  - `aria-live` para actualizar resultados y `role=alert` para errores.
  - **Justificación:** el usuario puede seguir el flujo completo desde requisitos hasta una decisión justificable sin abrir JSON manualmente.

- **`frontend/app/globals.css`**
  - Sistema visual responsive con tipografías, colores, tarjetas, tabla, scorecard, estados de error y layout móvil.
  - **Justificación:** la interfaz no es solo una prueba de conexión; la Fase 4 requiere una demo utilizable y presentable.

- **Mermaid dinámico**
  - Se carga mediante `import()` dentro de `useEffect`.
  - Se usa `securityLevel: "strict"`.
  - Si falla el renderizado, se conserva el código Mermaid como alternativa visible.
  - **Justificación:** evita bloquear la generación estática de Next.js y conserva una salida de diagnóstico aun si el SVG no puede renderizarse.

### 3.4 CORS y configuración API

- **`api/main.py`**
  - Se agregó `CORSMiddleware`.
  - El origen permitido se controla con `FRONTEND_ORIGINS`.
  - Default local: `http://localhost:3000`.
  - No se utiliza `allow_origins=["*"]`.
  - Se permiten únicamente métodos `GET` y `POST`, además de `Content-Type`.
  - Se agregó prueba de preflight CORS en `tests/test_api.py`.
  - **Justificación:** el navegador necesita un origen explícito para consumir la API y la configuración evita abrir el backend a cualquier sitio.

### 3.5 Documentación

- **`frontend/README.md`**
  - Incluye requisitos, desarrollo local, `NEXT_PUBLIC_API_URL`, `FRONTEND_ORIGINS` y quality gates.
- **`README.md`**
  - Actualizado a la Fase 4.
  - Documenta frontend, flujo de usuario, variables, CORS, comandos y estado real.
- **`ROADMAP.md`**
  - Fase 4 marcada como implementada, con despliegue público pendiente.

## 4. Flujo de ejecución

```text
Browser :3000
    │
    │ NEXT_PUBLIC_API_URL
    ▼
FastAPI :8000
    │
    ├── POST /architectures
    │      ├── Rule Engine
    │      ├── AI provider / template fallback
    │      └── Persistencia ArchSpec
    │
    └── GET /architectures/{id}/diagram
             │
             ▼
        Mermaid SVG en el cliente
```

## 5. Verificación

### Backend

```text
35 passed in 8.99s
TOTAL 476 statements, 91% coverage
Ruff: All checks passed!
Black: 26 files would be left unchanged.
uv lock --check: correcto
compileall: correcto
docker compose config --quiet: correcto
```

### Frontend

```text
npm run lint
0 errores, 0 warnings

npm run typecheck
correcto

npm run build
Compiled successfully
Routes:
  ○ /
  ○ /_not-found
```

### Smoke test HTTP

Se ejecutó `npm run start -- -p 3000` y se consultó la aplicación:

```text
GET http://127.0.0.1:3000
status: 200
contains InfraWise: true
```

### Dependencias

`npm ci` completó con el lockfile y generó/validó `frontend/package-lock.json`. npm reportó cinco vulnerabilidades de severidad alta en el árbol instalado. La consulta detallada de `npm audit` no pudo completarse porque el endpoint de auditoría del registry devolvió un error de red; por lo tanto, no se aplicó `npm audit fix --force` ni se modificaron dependencias a ciegas. Este punto queda como seguimiento de seguridad antes de publicar.

## 6. Limitaciones y pendientes

- No se publicó el frontend en Vercel, Netlify u otro proveedor.
- No se configuró un dominio público ni un secreto de producción.
- Docker Compose continúa levantando API + PostgreSQL; el frontend se ejecuta como proceso Next.js separado en desarrollo.
- El frontend no tiene todavía un test runner de componentes; su validación actual se basa en TypeScript, ESLint, build de producción y smoke test HTTP.
- El renderizado semántico de Mermaid se valida mediante build y fallback de código fuente; queda como mejora futura agregar pruebas visuales/browser automatizadas.
- Revisar las cinco vulnerabilidades npm cuando el registry de auditoría esté disponible.

## 7. Criterio de cierre

La Fase 4 se considera implementada porque existe un flujo frontend completo y verificable: captura requisitos, valida, llama a la API, recupera el diagrama, muestra costos, score y decisiones, y pasa los quality gates de lint, tipos y build. El despliegue público queda deliberadamente separado como actividad externa pendiente.
