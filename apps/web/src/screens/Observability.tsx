import { useEffect, useState } from "react";
import { apiGet } from "../api";
import { LineChart } from "../components/LineChart";
import { formatBytesGiB, formatDateSantiago, formatMetric } from "../format";
import type { HealthEntry, ObservabilityOverview, RangeResponse } from "../types";

const HEALTH_COLOR: Record<string, string> = {
  healthy: "green",
  degraded: "amber",
  unavailable: "red",
  error: "red",
  disabled: "gray",
  not_configured: "gray",
  configured_not_tested: "amber",
};

const RANGE_METRICS = [
  { key: "gpu_util_percent", label: "GPU uso (%)" },
  { key: "gpu_mem_used_bytes", label: "GPU memoria usada" },
  { key: "host_cpu_percent", label: "CPU host (%)" },
  { key: "host_mem_used_bytes", label: "RAM host usada" },
] as const;

const MINUTES_OPTIONS = [15, 30, 60, 180, 1440];

export function Observability() {
  const [overview, setOverview] = useState<ObservabilityOverview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await apiGet<ObservabilityOverview>("/api/observability/overview");
        if (!cancelled) {
          setOverview(res);
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    }
    void load();
    const interval = setInterval(() => void load(), 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!overview) {
    return (
      <div className="screen">
        <p>{error ? "No se pudo cargar la observabilidad." : "Cargando…"}</p>
      </div>
    );
  }

  const m = overview.metrics;

  return (
    <div className="screen">
      <section className="panel">
        <h2>Métricas actuales</h2>
        <div className="metric-grid">
          <MetricCard label="CPU host" value={formatMetric(m.host_cpu_percent.value, "%")} />
          <MetricCard
            label="RAM host"
            value={`${formatBytesGiB(m.host_mem_used_bytes.value)} / ${formatBytesGiB(m.host_mem_total_bytes.value)}`}
          />
          <MetricCard label="GPU uso" value={formatMetric(m.gpu_util_percent.value, "%")} />
          <MetricCard
            label="GPU memoria"
            value={`${formatBytesGiB(m.gpu_mem_used_bytes.value)} / ${formatBytesGiB(m.gpu_mem_total_bytes.value)}`}
          />
          <MetricCard
            label="GPU temperatura"
            value={m.gpu_temp_c.value !== null ? `${m.gpu_temp_c.value.toFixed(1)} ${m.gpu_temp_c.unit}` : "sin datos"}
            detail={m.gpu_temp_c.error}
          />
        </div>
      </section>

      <section className="panel">
        <h2>Salud de componentes</h2>
        <div className="health-grid">
          {Object.entries(overview.health).map(([name, entry]) => (
            <HealthCard key={name} name={name} entry={entry} />
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Uso de hoy</h2>
        <div className="usage-grid">
          <div>
            <h3>Por proveedor</h3>
            <ul>
              {Object.entries(overview.usage_today.by_provider).map(([p, count]) => (
                <li key={p}>
                  {p}: {count}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Gasto</h3>
            <ul>
              <li>Reservado abierto: USD {overview.usage_today.spent.reserved_open.toFixed(4)}</li>
              <li>Contabilizado: USD {overview.usage_today.spent.accounted.toFixed(4)}</li>
              <li>Llamadas de costo desconocido: {overview.usage_today.spent.unknown_cost_calls}</li>
              <li>Llamadas totales: {overview.usage_today.spent.calls}</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Solicitudes recientes</h2>
        {overview.recent_requests.length === 0 ? (
          <p>Sin solicitudes recientes.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Inicio</th>
                <th>Ruta</th>
                <th>Proveedor</th>
                <th>Modelo</th>
                <th>Estado</th>
                <th>Duración</th>
              </tr>
            </thead>
            <tbody>
              {overview.recent_requests.map((r) => (
                <tr key={r.request_id}>
                  <td>{r.request_id}</td>
                  <td>{formatDateSantiago(r.started_at)}</td>
                  <td>{r.route}</td>
                  <td>{r.provider}</td>
                  <td>{r.model}</td>
                  <td>{r.status}</td>
                  <td>{r.duration_s.toFixed(2)} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <h2>Dashboard ALICE / OVERVIEW</h2>
        {overview.grafana_url ? (
          <a href={overview.grafana_url} target="_blank" rel="noopener noreferrer">
            {overview.grafana_url}
          </a>
        ) : (
          <p>Grafana no está configurado.</p>
        )}
        <p className="hint">
          Grafana escucha en 127.0.0.1; desde la tailnet se publica con login Viewer (usuario «viewer»). Si no tienes acceso, usa esta vista o el acceso Viewer de la
          tailnet si está configurado.
        </p>
      </section>

      <RangeCharts />
    </div>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="metric-card">
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">{value}</div>
      {detail && <div className="metric-card__detail">{detail}</div>}
    </div>
  );
}

export function HealthCard({ name, entry }: { name: string; entry: HealthEntry }) {
  const color = HEALTH_COLOR[entry.state] ?? "gray";
  return (
    <div className={`health-card health-card--${color}`}>
      <div className="health-card__name">{name}</div>
      <div className="health-card__state">{entry.state}</div>
      {entry.detail && <div className="health-card__detail">{entry.detail}</div>}
    </div>
  );
}

function RangeCharts() {
  const [minutes, setMinutes] = useState(60);
  const [ranges, setRanges] = useState<Record<string, RangeResponse | null>>({});

  useEffect(() => {
    let cancelled = false;
    async function load() {
      for (const metric of RANGE_METRICS) {
        try {
          const res = await apiGet<RangeResponse>(`/api/observability/range?metric=${metric.key}&minutes=${minutes}`);
          if (!cancelled) setRanges((prev) => ({ ...prev, [metric.key]: res }));
        } catch {
          if (!cancelled) setRanges((prev) => ({ ...prev, [metric.key]: null }));
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [minutes]);

  return (
    <section className="panel">
      <h2>Históricos</h2>
      <label htmlFor="range-minutes">Rango</label>
      <select id="range-minutes" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
        {MINUTES_OPTIONS.map((mi) => (
          <option key={mi} value={mi}>
            {mi} min
          </option>
        ))}
      </select>
      <div className="chart-grid">
        {RANGE_METRICS.map((metric) => {
          const range = ranges[metric.key];
          const points = range?.series[0]?.points ?? [];
          return (
            <div key={metric.key} className="chart-card">
              <h3>{metric.label}</h3>
              {range && range.coverage.fraction < 0.9 && range.coverage.gaps.length > 0 && (
                <p className="notice notice--warning">
                  Cobertura incompleta ({Math.round(range.coverage.fraction * 100)}%).
                </p>
              )}
              <LineChart points={points} unit={range?.unit} />
            </div>
          );
        })}
      </div>
    </section>
  );
}
