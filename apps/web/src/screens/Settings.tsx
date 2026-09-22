import { useEffect, useState } from "react";
import { apiGet, apiSend } from "../api";
import type { SettingsResponse } from "../types";

const FEATURE_REASON: Record<string, string> = {
  hermes: "Deshabilitado por política.",
  grafana_external: "Deshabilitado por defecto.",
  email: "Deshabilitado por defecto.",
  notebooklm: "Deshabilitado por defecto.",
  loki: "Deshabilitado por defecto.",
  docker: "No instalado en este beta.",
};

export function Settings() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<SettingsResponse>("/api/settings")
      .then(setData)
      .catch(() => setData(null));
  }, []);

  async function toggleLocalOnly() {
    if (!data) return;
    setSaving(true);
    setError(null);
    const next = !data.local_only;
    try {
      await apiSend<SettingsResponse>("/api/settings", "PUT", { local_only: next });
      setData({ ...data, local_only: next });
    } catch {
      setError("No se pudo actualizar el ajuste.");
    } finally {
      setSaving(false);
    }
  }

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
        <h2>Solo local</h2>
        <p className="hint">Bloquea en el backend toda salida de contenido hacia proveedores externos.</p>
        <label className="switch">
          <input type="checkbox" checked={data.local_only} onChange={() => void toggleLocalOnly()} disabled={saving} />
          <span>{data.local_only ? "Activado" : "Desactivado"}</span>
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </section>

      <section className="panel">
        <h2>General</h2>
        <ul>
          <li>Nube habilitada: {data.cloud_enabled ? "sí" : "no"}</li>
          <li>Presupuesto por solicitud: USD {data.budget_per_request_usd.toFixed(2)}</li>
          <li>Presupuesto diario: USD {data.budget_daily_usd.toFixed(2)}</li>
          <li>Zona horaria: {data.timezone}</li>
          <li>Límite de subida: {data.max_upload_mb} MB</li>
        </ul>
      </section>

      <section className="panel">
        <h2>Credenciales</h2>
        <ul>
          {Object.entries(data.credentials).map(([name, state]) => (
            <li key={name}>
              {name}: {state}
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Integraciones</h2>
        <ul>
          {Object.entries(data.features).map(([name, enabled]) => (
            <li key={name}>
              {name}: {enabled ? "habilitado" : "deshabilitado"}
              {!enabled && FEATURE_REASON[name] && <span className="hint"> — {FEATURE_REASON[name]}</span>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
