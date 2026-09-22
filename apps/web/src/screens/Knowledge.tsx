import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { apiGet, apiSend, ApiError } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { formatBytesAuto, formatDateSantiago } from "../format";
import type { DatasetItem, DocumentItem, FactItem, FactsResponse, Privacy } from "../types";

type Tab = "documents" | "datasets" | "facts";

const STATUS_LABEL: Record<DocumentItem["status"], string> = {
  pending: "pendiente",
  processing: "procesando",
  ready: "listo",
  failed: "fallido",
};

export function Knowledge() {
  const [tab, setTab] = useState<Tab>("documents");
  return (
    <div className="screen">
      <div className="tabs">
        <button type="button" className={`tab${tab === "documents" ? " tab--active" : ""}`} onClick={() => setTab("documents")}>
          Documentos
        </button>
        <button type="button" className={`tab${tab === "datasets" ? " tab--active" : ""}`} onClick={() => setTab("datasets")}>
          Datasets
        </button>
        <button type="button" className={`tab${tab === "facts" ? " tab--active" : ""}`} onClick={() => setTab("facts")}>
          Hechos verificados
        </button>
      </div>
      {tab === "documents" && <DocumentsPanel />}
      {tab === "datasets" && <DatasetsPanel />}
      {tab === "facts" && <FactsPanel />}
    </div>
  );
}

function DocumentsPanel() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadPrivacy, setUploadPrivacy] = useState<Privacy>("PRIVATE");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const docs = await apiGet<DocumentItem[]>("/api/documents");
      setDocuments(docs);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    const hasActive = documents.some((d) => d.status === "pending" || d.status === "processing");
    if (!hasActive) return;
    const interval = setInterval(() => void load(), 2000);
    return () => clearInterval(interval);
  }, [documents]);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setNotice(null);
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("privacy", uploadPrivacy);
    try {
      const res = await apiSend<{ document: DocumentItem; duplicate: boolean }>("/api/documents", "POST", form);
      if (res.duplicate) setNotice("El archivo ya existía (duplicado detectado).");
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setUploadError(err.detail ?? "Archivo inválido.");
      } else {
        setUploadError("No se pudo subir el archivo.");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleCancel(id: string) {
    await apiSend(`/api/documents/${id}/cancel`, "POST");
    await load();
  }
  async function handleRetry(id: string) {
    await apiSend(`/api/documents/${id}/retry`, "POST");
    await load();
  }
  async function handleDelete(id: string) {
    await apiSend(`/api/documents/${id}`, "DELETE");
    setConfirmDeleteId(null);
    await load();
  }

  return (
    <div>
      <section className="panel">
        <h2>Subir documento</h2>
        <p className="hint">
          Formatos soportados: PDF (con texto), Markdown, TXT, LOG, CSV, XLSX. Límite 50 MB. PDF escaneado requiere
          OCR (no soportado).
        </p>
        <div className="upload-row">
          <label htmlFor="upload-privacy">Privacidad</label>
          <select id="upload-privacy" value={uploadPrivacy} onChange={(e) => setUploadPrivacy(e.target.value as Privacy)}>
            <option value="PRIVATE">PRIVATE</option>
            <option value="INTERNAL">INTERNAL</option>
            <option value="PUBLIC">PUBLIC</option>
          </select>
          <label htmlFor="upload-file">Archivo</label>
          <input id="upload-file" ref={fileInputRef} type="file" onChange={handleUpload} disabled={uploading} />
        </div>
        {notice && <p className="notice">{notice}</p>}
        {uploadError && (
          <p className="form-error" role="alert">
            {uploadError}
          </p>
        )}
      </section>

      <section className="panel">
        <h2>Documentos</h2>
        {loading ? (
          <p>Cargando…</p>
        ) : documents.length === 0 ? (
          <p>No hay documentos.</p>
        ) : (
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.document_id} className="doc-item">
                <div className="doc-item__main">
                  <a href={`/api/documents/${doc.document_id}/file`} target="_blank" rel="noopener noreferrer">
                    {doc.original_name}
                  </a>
                  <span className={`badge badge--${doc.status}`}>{STATUS_LABEL[doc.status]}</span>
                  <span className="badge">{doc.privacy}</span>
                  <span className="badge">{doc.verification}</span>
                </div>
                <div className="doc-item__meta">
                  v{doc.version} · {formatBytesAuto(doc.size_bytes)} · {formatDateSantiago(doc.ingested_at)}
                  {doc.chunks !== null && <> · {doc.chunks} fragmentos</>}
                </div>
                {doc.status_detail && <div className="doc-item__detail">{doc.status_detail}</div>}
                <div className="doc-item__actions">
                  {doc.status === "processing" && (
                    <button type="button" className="btn" onClick={() => void handleCancel(doc.document_id)}>
                      Cancelar
                    </button>
                  )}
                  {doc.status === "failed" && (
                    <button type="button" className="btn" onClick={() => void handleRetry(doc.document_id)}>
                      Reintentar
                    </button>
                  )}
                  <button type="button" className="btn btn--danger" onClick={() => setConfirmDeleteId(doc.document_id)}>
                    Eliminar
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {confirmDeleteId && (
        <ConfirmDialog
          title="Eliminar documento"
          message="Esta acción no se puede deshacer. ¿Deseas continuar?"
          confirmLabel="Eliminar"
          onConfirm={() => void handleDelete(confirmDeleteId)}
          onCancel={() => setConfirmDeleteId(null)}
        />
      )}
    </div>
  );
}

function DatasetsPanel() {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<DatasetItem[]>("/api/datasets")
      .then(setDatasets)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Cargando…</p>;
  if (datasets.length === 0) return <p>No hay datasets.</p>;

  return (
    <table className="table">
      <thead>
        <tr>
          <th>Tabla</th>
          <th>Documento</th>
          <th>Dueño</th>
          <th>Privacidad</th>
          <th>Columnas</th>
          <th>Filas</th>
        </tr>
      </thead>
      <tbody>
        {datasets.map((d) => {
          let columns: string[] = [];
          try {
            columns = JSON.parse(d.columns_json) as string[];
          } catch {
            columns = [];
          }
          return (
            <tr key={d.table_name}>
              <td>{d.table_name}</td>
              <td>{d.document_id}</td>
              <td>{d.owner}</td>
              <td>{d.privacy}</td>
              <td>{columns.join(", ")}</td>
              <td>{d.row_count}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

interface FactFormState {
  subject_key: string;
  statement: string;
  privacy: Privacy;
  verification: FactItem["verification"];
  source_id: string;
  source_location: string;
  verified_by: string;
  notes: string;
}

const EMPTY_FORM: FactFormState = {
  subject_key: "",
  statement: "",
  privacy: "PRIVATE",
  verification: "UNVERIFIED",
  source_id: "",
  source_location: "",
  verified_by: "",
  notes: "",
};

function FactsPanel() {
  const [subject, setSubject] = useState("");
  const [data, setData] = useState<FactsResponse>({ facts: [], conflict: [] });
  const [loading, setLoading] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<FactFormState>(EMPTY_FORM);

  useEffect(() => {
    setLoading(true);
    const path = subject ? `/api/facts?subject=${encodeURIComponent(subject)}` : "/api/facts";
    apiGet<FactsResponse>(path)
      .then(setData)
      .finally(() => setLoading(false));
  }, [subject]);

  async function reload() {
    const path = subject ? `/api/facts?subject=${encodeURIComponent(subject)}` : "/api/facts";
    setData(await apiGet<FactsResponse>(path));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (form.verification === "VERIFIED" && !form.verified_by.trim()) {
      setFormError("verified_by es obligatorio para hechos VERIFIED.");
      return;
    }
    try {
      await apiSend("/api/facts", "POST", {
        subject_key: form.subject_key,
        statement: form.statement,
        privacy: form.privacy,
        verification: form.verification,
        source_id: form.source_id,
        source_location: form.source_location || undefined,
        verified_by: form.verified_by || undefined,
        notes: form.notes || undefined,
      });
      setForm(EMPTY_FORM);
      await reload();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setFormError(err.detail ?? "Datos inválidos.");
      } else {
        setFormError("No se pudo guardar el hecho.");
      }
    }
  }

  return (
    <div>
      <section className="panel">
        <label htmlFor="fact-subject">Filtrar por subject_key</label>
        <input id="fact-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
      </section>

      {data.conflict.length > 0 && (
        <section className="panel panel--warning">
          <h2>Conflicto entre hechos VERIFIED</h2>
          <ul>
            {data.conflict.map((f) => (
              <li key={f.fact_id}>
                {f.statement} — fuente: {f.source_id}
                {f.source_location ? ` (${f.source_location})` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="panel">
        <h2>Hechos</h2>
        {loading ? (
          <p>Cargando…</p>
        ) : data.facts.length === 0 ? (
          <p>No hay hechos.</p>
        ) : (
          <ul className="fact-list">
            {data.facts.map((f) => (
              <li key={f.fact_id}>
                <strong>{f.subject_key}:</strong> {f.statement}
                <div className="doc-item__meta">
                  {f.verification} · {f.privacy} · fuente {f.source_id}
                  {f.verified_by ? ` · verificado por ${f.verified_by}` : ""}
                </div>
                {f.notes && <div className="doc-item__detail">{f.notes}</div>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2>Agregar hecho</h2>
        <form onSubmit={(e) => void handleSubmit(e)}>
          <label htmlFor="f-subject">subject_key</label>
          <input
            id="f-subject"
            value={form.subject_key}
            onChange={(e) => setForm({ ...form, subject_key: e.target.value })}
            required
          />

          <label htmlFor="f-statement">statement</label>
          <textarea
            id="f-statement"
            value={form.statement}
            onChange={(e) => setForm({ ...form, statement: e.target.value })}
            required
          />

          <label htmlFor="f-privacy">privacy</label>
          <select id="f-privacy" value={form.privacy} onChange={(e) => setForm({ ...form, privacy: e.target.value as Privacy })}>
            <option value="PRIVATE">PRIVATE</option>
            <option value="INTERNAL">INTERNAL</option>
            <option value="PUBLIC">PUBLIC</option>
          </select>

          <label htmlFor="f-verification">verification</label>
          <select
            id="f-verification"
            value={form.verification}
            onChange={(e) => setForm({ ...form, verification: e.target.value as FactItem["verification"] })}
          >
            <option value="UNVERIFIED">UNVERIFIED</option>
            <option value="EMPIRICAL">EMPIRICAL</option>
            <option value="VERIFIED">VERIFIED</option>
          </select>

          <label htmlFor="f-source">source_id</label>
          <input id="f-source" value={form.source_id} onChange={(e) => setForm({ ...form, source_id: e.target.value })} required />

          <label htmlFor="f-location">source_location (opcional)</label>
          <input
            id="f-location"
            value={form.source_location}
            onChange={(e) => setForm({ ...form, source_location: e.target.value })}
          />

          <label htmlFor="f-verified-by">
            verified_by {form.verification === "VERIFIED" ? "(obligatorio)" : "(opcional)"}
          </label>
          <input
            id="f-verified-by"
            value={form.verified_by}
            onChange={(e) => setForm({ ...form, verified_by: e.target.value })}
          />

          <label htmlFor="f-notes">notes (opcional)</label>
          <textarea id="f-notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />

          {formError && (
            <p className="form-error" role="alert">
              {formError}
            </p>
          )}

          <button type="submit" className="btn btn--primary">
            Guardar
          </button>
        </form>
      </section>
    </div>
  );
}
