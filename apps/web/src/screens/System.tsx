import { useEffect, useState } from "react";
import { apiGet } from "../api";
import type { SystemResponse } from "../types";
import { HealthCard } from "./Observability";

export function System() {
  const [data, setData] = useState<SystemResponse | null>(null);

  useEffect(() => {
    apiGet<SystemResponse>("/api/system")
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) {
    return (
      <div className="screen">
        <p>Cargando…</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <section className="panel">
        <h2>Versión</h2>
        <p>{data.version}</p>
      </section>

      <section className="panel">
        <h2>Salud de componentes</h2>
        <div className="health-grid">
          {Object.entries(data.health).map(([name, entry]) => (
            <HealthCard key={name} name={name} entry={entry} />
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Modo</h2>
        <p>Solo local: {data.local_only ? "sí" : "no"}</p>
      </section>

      <section className="panel">
        <h2>Presupuesto</h2>
        <ul>
          <li>Por solicitud: USD {data.budget.per_request_usd.toFixed(2)}</li>
          <li>Diario: USD {data.budget.daily_usd.toFixed(2)}</li>
          <li>Reservado abierto hoy: USD {data.budget.today.reserved_open.toFixed(4)}</li>
          <li>Contabilizado hoy: USD {data.budget.today.accounted.toFixed(4)}</li>
          <li>Llamadas de costo desconocido: {data.budget.today.unknown_cost_calls}</li>
          <li>Llamadas totales hoy: {data.budget.today.calls}</li>
        </ul>
      </section>

      <section className="panel">
        <h2>Acceso remoto</h2>
        <p>Origen público: {data.remote.public_origin ?? "no configurado"}</p>
        <p>Esta sesión llega vía proxy de Tailscale: {data.remote.via_proxy ? "sí" : "no"}</p>
      </section>

      <section className="panel">
        <h2>Grafana local</h2>
        {data.grafana_local ? (
          <a href={data.grafana_local} target="_blank" rel="noopener noreferrer">
            {data.grafana_local}
          </a>
        ) : (
          <p>No configurado.</p>
        )}
      </section>
    </div>
  );
}
