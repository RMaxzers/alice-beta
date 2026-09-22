import { useEffect, useState } from "react";
import { apiGet } from "../api";
import { formatBytesAuto } from "../format";
import type { ModelsResponse } from "../types";

const FUTURE_LABEL: Record<string, string> = {
  DISABLED: "deshabilitado",
  READY_FOR_CONFIGURATION: "listo para configurar",
};

export function Models() {
  const [data, setData] = useState<ModelsResponse | null>(null);

  useEffect(() => {
    apiGet<ModelsResponse>("/api/models")
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
        <h2>Estado de Ollama</h2>
        <p>{data.ollama_reachable ? "Alcanzable" : "No alcanzable"}</p>
      </section>

      <section className="panel">
        <h2>Modelos disponibles</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Alias</th>
              <th>Proveedor</th>
              <th>Modelo real</th>
              <th>Ubicación</th>
              <th>Disponible</th>
              <th>Cargado en VRAM</th>
              <th>Precio (USD/Mtok in / out)</th>
            </tr>
          </thead>
          <tbody>
            {data.aliases.map((a) => (
              <tr key={a.alias}>
                <td>{a.alias}</td>
                <td>{a.provider}</td>
                <td>{a.model}</td>
                <td>{a.location}</td>
                <td>{a.available ? "sí" : "no"}</td>
                <td>
                  {a.loaded === undefined
                    ? "—"
                    : a.loaded
                      ? `sí${a.vram_bytes !== undefined ? ` (${formatBytesAuto(a.vram_bytes)})` : ""}`
                      : "no"}
                </td>
                <td>{a.pricing ? `${a.pricing.usd_per_mtok_in} / ${a.pricing.usd_per_mtok_out}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Ruta → alias</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Ruta</th>
              <th>Alias</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.routes).map(([route, alias]) => (
              <tr key={route}>
                <td>{route}</td>
                <td>{alias}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Proveedores futuros</h2>
        <ul>
          {Object.entries(data.future_providers).map(([provider, state]) => (
            <li key={provider}>
              {provider}: {FUTURE_LABEL[state] ?? state}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
