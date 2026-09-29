"use client";

import { FormEvent, useEffect, useState } from "react";

import type { ArchSpec, Requirements } from "@/lib/types";
import { DEFAULT_REQUIREMENTS, validateRequirements } from "@/lib/validation";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const appTypes: Array<[Requirements["app_type"], string]> = [
  ["web_api", "Web API"],
  ["web_app", "Aplicación web"],
  ["static_site", "Sitio estático"],
  ["background_worker", "Background worker"],
];
const databaseOptions: Array<[Requirements["database"], string]> = [
  ["postgresql", "PostgreSQL"],
  ["mysql", "MySQL"],
  ["none", "Sin base de datos"],
];
const availabilityOptions: Array<[Requirements["availability"], string]> = [
  ["standard", "Standard · 99.5%"],
  ["high", "High · 99.9%"],
  ["critical", "Critical · 99.99%"],
];
const optimizationOptions: Array<[Requirements["optimize_for"], string]> = [
  ["balanced", "Balanceado"],
  ["cost", "Costo"],
  ["performance", "Performance"],
  ["availability", "Disponibilidad"],
  ["simplicity", "Simplicidad"],
];

function currency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function MermaidDiagram({ diagram }: { diagram: string }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "base",
          themeVariables: {
            primaryColor: "#dff7ee",
            primaryTextColor: "#10231e",
            primaryBorderColor: "#1f9d73",
            lineColor: "#6a7a75",
          },
        });
        const result = await mermaid.render(`architecture-${Date.now()}`, diagram);
        if (active) {
          setSvg(result.svg);
          setError("");
        }
      } catch {
        if (active) {
          setError("No se pudo dibujar el diagrama. Puedes consultar el Mermaid generado abajo.");
          setSvg("");
        }
      }
    }
    void render();
    return () => {
      active = false;
    };
  }, [diagram]);

  return (
    <div className="diagram-wrap">
      {svg ? <div className="diagram-svg" dangerouslySetInnerHTML={{ __html: svg }} /> : null}
      {error ? <p className="inline-error">{error}</p> : null}
      <details className="source-details">
        <summary>Ver código Mermaid</summary>
        <pre className="code-block">{diagram}</pre>
      </details>
    </div>
  );
}

function ScoreCard({ score }: { score: NonNullable<ArchSpec["score"]> }) {
  const values = [
    ["Complejidad", score.complexity],
    ["Escalabilidad", score.scalability],
    ["Disponibilidad", `${score.availability_pct}%`],
    ["Carga operativa", score.operational_overhead],
  ];
  return (
    <div className="score-grid">
      {values.map(([label, value]) => (
        <div className="score-item" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function Home() {
  const [form, setForm] = useState<Requirements>(DEFAULT_REQUIREMENTS);
  const [result, setResult] = useState<ArchSpec | null>(null);
  const [diagram, setDiagram] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateField<K extends keyof Requirements>(field: K, value: Requirements[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateRequirements(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/architectures`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const payload = (await response.json()) as ArchSpec | { detail?: string };
      if (!response.ok) {
        throw new Error("detail" in payload && payload.detail ? payload.detail : "La API rechazó la solicitud.");
      }
      const spec = payload as ArchSpec;
      setResult(spec);
      const diagramResponse = await fetch(`${API_URL}/architectures/${spec.id}/diagram`);
      setDiagram(diagramResponse.ok ? await diagramResponse.text() : "");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo conectar con la API.");
      setResult(null);
      setDiagram("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="InfraWise inicio">
          <span className="brand-mark">IW</span>
          <span>InfraWise</span>
        </a>
        <span className="phase-pill">PHASE 04 · ADVISOR</span>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">FINOPS · CLOUD ARCHITECTURE · EXPLAINABLE AI</p>
          <h1>Diseña con intención.<br /><em>Despliega con evidencia.</em></h1>
          <p className="hero-text">
            Describe tu carga de trabajo y recibe una arquitectura AWS con costo,
            trade-offs y decisiones explicadas. Sin magia negra: cada componente nace de tus requisitos.
          </p>
          <div className="hero-stats">
            <span><b>01</b> Requisitos tipados</span>
            <span><b>02</b> Motor determinista</span>
            <span><b>03</b> Decisiones auditables</span>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit orbit-one"><span>cost</span></div>
          <div className="orbit orbit-two"><span>scale</span></div>
          <div className="orbit orbit-three"><span>trust</span></div>
          <div className="orbit-core"><span>IW</span></div>
        </div>
      </section>

      <section className="workspace" aria-label="Architecture advisor">
        <div className="section-heading">
          <div>
            <p className="eyebrow">01 / INPUT MODEL</p>
            <h2>Cuéntanos qué necesitas.</h2>
          </div>
          <p className="section-note">Los límites se validan en cliente y vuelven a validarse en la API.</p>
        </div>

        <form className="requirements-card" onSubmit={submit}>
          <div className="field-grid">
            <label>
              <span>Tipo de aplicación</span>
              <select value={form.app_type} onChange={(event) => updateField("app_type", event.target.value as Requirements["app_type"])}>
                {appTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              <span>Base de datos</span>
              <select value={form.database} onChange={(event) => updateField("database", event.target.value as Requirements["database"])}>
                {databaseOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              <span>Usuarios activos / mes</span>
              <input type="number" min="1" value={form.monthly_active_users} onChange={(event) => updateField("monthly_active_users", Number(event.target.value))} />
            </label>
            <label>
              <span>Requests por minuto</span>
              <input type="number" min="1" value={form.requests_per_minute} onChange={(event) => updateField("requests_per_minute", Number(event.target.value))} />
            </label>
            <label>
              <span>Almacenamiento (GB)</span>
              <input type="number" min="0" step="0.1" value={form.storage_gb} onChange={(event) => updateField("storage_gb", Number(event.target.value))} />
            </label>
            <label>
              <span>Presupuesto mensual (USD)</span>
              <input type="number" min="0.01" step="0.01" value={form.monthly_budget_usd} onChange={(event) => updateField("monthly_budget_usd", Number(event.target.value))} />
            </label>
            <label>
              <span>Disponibilidad</span>
              <select value={form.availability} onChange={(event) => updateField("availability", event.target.value as Requirements["availability"])}>
                {availabilityOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              <span>Optimizar para</span>
              <select value={form.optimize_for} onChange={(event) => updateField("optimize_for", event.target.value as Requirements["optimize_for"])}>
                {optimizationOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className="field-wide">
              <span>Región AWS</span>
              <input value={form.region} onChange={(event) => updateField("region", event.target.value)} placeholder="us-east-1" />
            </label>
          </div>
          <div className="form-footer">
            <span className="form-hint">El motor selecciona la opción más barata que cumple tus restricciones.</span>
            <button type="submit" disabled={loading}>
              {loading ? "Analizando…" : "Generar arquitectura"}
              <span aria-hidden="true">↗</span>
            </button>
          </div>
          {error ? <p className="error-banner" role="alert">{error}</p> : null}
        </form>
      </section>

      {result ? (
        <section className="results" aria-live="polite">
          <div className="section-heading result-heading">
            <div>
              <p className="eyebrow">02 / DECISION OUTPUT</p>
              <h2>Una arquitectura que puedes defender.</h2>
            </div>
            <div className="result-id">{result.id}</div>
          </div>

          <div className="summary-strip">
            <div><span>Costo mensual estimado</span><strong>{currency(result.total_monthly_cost_usd)}</strong></div>
            <div><span>Presupuesto</span><strong>{currency(result.requirements.monthly_budget_usd)}</strong></div>
            <div><span>Margen</span><strong>{currency(result.requirements.monthly_budget_usd - result.total_monthly_cost_usd)}</strong></div>
            <div><span>Componentes</span><strong>{result.components.length}</strong></div>
          </div>

          <div className="result-grid">
            <article className="panel panel-large">
              <div className="panel-title"><span>ARCHITECTURE MAP</span><span className="live-dot">● LIVE</span></div>
              {diagram ? <MermaidDiagram diagram={diagram} /> : <p className="muted">El diagrama no está disponible.</p>}
            </article>
            <article className="panel">
              <div className="panel-title"><span>SCORECARD</span><span>v0.4</span></div>
              {result.score ? <ScoreCard score={result.score} /> : <p className="muted">Sin score disponible.</p>}
              <div className="score-explanation">La puntuación resume costo, complejidad, margen de escalabilidad, disponibilidad y carga operativa.</div>
            </article>
          </div>

          <div className="result-grid lower-grid">
            <article className="panel panel-table">
              <div className="panel-title"><span>COST BREAKDOWN</span><span>USD / MONTH</span></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Servicio</th><th>Categoría</th><th>Qty</th><th>Costo</th></tr></thead>
                  <tbody>
                    {result.components.map((component) => (
                      <tr key={component.id}>
                        <td><strong>{component.display_name}</strong><small>{component.service_id}</small></td>
                        <td><span className="category-tag">{component.category}</span></td>
                        <td>{component.count}</td>
                        <td>{currency(component.estimated_monthly_cost_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot><tr><td colSpan={3}>TOTAL MONTHLY</td><td>{currency(result.total_monthly_cost_usd)}</td></tr></tfoot>
                </table>
              </div>
            </article>
            <article className="panel decisions-panel">
              <div className="panel-title"><span>WHY THIS STACK?</span><span>{result.decisions.length} DECISIONS</span></div>
              <div className="decision-list">
                {result.decisions.map((decision, index) => (
                  <div className="decision" key={decision.component_id}>
                    <span className="decision-index">0{index + 1}</span>
                    <div><strong>{result.components.find((component) => component.id === decision.component_id)?.display_name ?? decision.component_id}</strong><p>{decision.reasoning}</p></div>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>
      ) : (
        <section className="empty-state">
          <span className="empty-line" />
          <p>Tu arquitectura aparecerá aquí.</p>
          <span className="empty-line" />
        </section>
      )}

      <footer><span>INFRAWISE / CLOUD ARCHITECTURE ADVISOR</span><span>DETERMINISTIC BY DESIGN · PHASE 04</span></footer>
    </main>
  );
}
