import type { AuthorizationPreview } from "../types";

export function AuthorizationModal({
  preview,
  busy,
  onAuthorizeOnce,
  onContinueLocal,
  onCancel,
}: {
  preview: AuthorizationPreview;
  busy: boolean;
  onAuthorizeOnce: () => void;
  onContinueLocal: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <div className="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <h3 id="auth-title">Autorización requerida para salir del equipo</h3>
        <dl className="auth-details">
          <dt>Proveedor</dt>
          <dd>{preview.provider}</dd>
          <dt>Destinatarios</dt>
          <dd>{preview.recipients.length ? preview.recipients.join(", ") : "—"}</dd>
          <dt>Modelo</dt>
          <dd>{preview.model}</dd>
          <dt>Privacidad</dt>
          <dd>{preview.privacy}</dd>
          <dt>Motivo</dt>
          <dd>{preview.reason}</dd>
          <dt>Campos que se enviarán</dt>
          <dd>{preview.fields.length ? preview.fields.join(", ") : "—"}</dd>
          <dt>Costo estimado</dt>
          <dd>
            {preview.estimated_cost_usd !== null
              ? `USD ${preview.estimated_cost_usd.toFixed(4)}`
              : "desconocido"}
          </dd>
        </dl>
        <p>Vista previa exacta del contenido que se enviará:</p>
        <pre className="auth-preview">{preview.payload_preview}</pre>
        <div className="modal__actions modal__actions--wrap">
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>
            Cancelar
          </button>
          <button type="button" className="btn" onClick={onContinueLocal} disabled={busy}>
            Continuar localmente
          </button>
          <button type="button" className="btn btn--primary" onClick={onAuthorizeOnce} disabled={busy}>
            Autorizar una vez
          </button>
        </div>
      </div>
    </div>
  );
}
