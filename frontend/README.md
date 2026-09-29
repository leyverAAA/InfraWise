# InfraWise Frontend

Frontend Next.js de InfraWise para diseñar una arquitectura AWS a partir de requisitos declarativos.

## Desarrollo

Requiere Node.js 20.9+ y npm.

```bash
npm install
npm run dev
```

Abre `http://localhost:3000`.

La API por defecto es `http://localhost:8000`. Para usar otra URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

El backend debe permitir el origen del frontend mediante:

```bash
FRONTEND_ORIGINS=http://localhost:3000
```

## Quality gates

```bash
npm run lint
npm run typecheck
npm run build
npm run start -- -p 3000
```

La aplicación contiene validación cliente para los límites de `Requirements`, un formulario de generación, tabla de costos, `ScoreCard`, decisiones explicadas y renderizado Mermaid.
