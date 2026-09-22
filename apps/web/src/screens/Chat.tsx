import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { apiGet, apiSend, streamChat, ApiError } from "../api";
import { Markdown } from "../markdown";
import { AuthorizationModal } from "../components/AuthorizationModal";
import type {
  AuthorizationPreview,
  ChatHistoryTurn,
  ChatRequest,
  DocumentItem,
  LogoState,
  Privacy,
  Route,
  RouteDecision,
  SourceItem,
  ToolEvent,
} from "../types";

const ROUTES: Route[] = [
  "LOCAL_SIMPLE",
  "LOCAL_CODE",
  "LOCAL_RAG",
  "CLOUD_CHEAP",
  "CLOUD_POWERFUL",
  "WEB_RESEARCH",
  "FINANCIAL_RESEARCH",
  "OBSERVABILITY",
  "AUTOMATION",
  "STRUCTURED_QUERY",
  "LOG_ANALYSIS",
];

const EXAMPLE_PROMPTS = [
  "¿Cómo está Alice?",
  "Explícame qué es una VLAN.",
  "¿Cuántos activos del inventario están fuera de soporte?",
  "¿Qué ocurrió con CPU, RAM y GPU durante mi última consulta?",
  "Investiga las novedades recientes de Ollama.",
  "Resume el último documento que subí.",
];

interface DoneInfo {
  request_id: string;
  provider: string;
  model: string;
  latency_s: number;
  queue_s: number;
  retrieval_s: number;
  tokens_out: number;
  cost_usd: number | null;
  cost_state: "local" | "reported" | "unknown";
  privacy: Privacy;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  privacy: Privacy;
  status: "streaming" | "done" | "error" | "cancelled" | "pending-auth";
  decision?: RouteDecision;
  raisedBy?: string[];
  tools: ToolEvent[];
  sources?: SourceItem[];
  done?: DoneInfo;
  error?: string;
  authPreview?: AuthorizationPreview;
  requestBody?: ChatRequest;
  showDetails?: boolean;
}

function routeToLogoState(route: Route): LogoState {
  if (route === "LOCAL_RAG") return "knowledge";
  if (route === "OBSERVABILITY") return "observability";
  if (route === "CLOUD_CHEAP" || route === "CLOUD_POWERFUL" || route === "WEB_RESEARCH" || route === "FINANCIAL_RESEARCH") {
    return "cloud";
  }
  return "local";
}

function buildHistory(list: ChatMessage[]): ChatHistoryTurn[] {
  const turns: ChatHistoryTurn[] = [];
  for (const m of list) {
    if (m.role === "user") {
      turns.push({ role: "user", content: m.content, privacy: m.privacy });
    } else if (m.role === "assistant" && m.status === "done") {
      turns.push({ role: "assistant", content: m.content, privacy: m.decision?.privacy ?? m.privacy });
    }
  }
  return turns.slice(-10);
}

function formatCost(done?: DoneInfo): string {
  if (!done) return "";
  if (done.cost_state === "local") return "local";
  if (done.cost_state === "reported") return `USD ${(done.cost_usd ?? 0).toFixed(4)} (reportado)`;
  return "desconocido";
}

function newId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `id-${Date.now()}-${Math.random()}`;
}

export function Chat({ onLogoState }: { onLogoState: (s: LogoState) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [privacy, setPrivacy] = useState<Privacy>("PRIVATE");
  const [routeOverride, setRouteOverride] = useState<Route | "">("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [attachedIds, setAttachedIds] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    apiGet<DocumentItem[]>("/api/documents")
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  function updateMessage(id: string, patch: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)) {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) } : m)),
    );
  }

  async function runStream(assistantId: string, body: ChatRequest) {
    const controller = new AbortController();
    abortRef.current = controller;
    setSending(true);
    onLogoState("routing");
    try {
      for await (const event of streamChat(body, controller.signal)) {
        if (event.type === "route") {
          const decision = event.decision;
          const raisedBy = event.raised_by;
          onLogoState(routeToLogoState(decision.route));
          updateMessage(assistantId, { decision, raisedBy });
        } else if (event.type === "tool") {
          const tool: ToolEvent = event;
          updateMessage(assistantId, (m) => ({ tools: [...m.tools, tool] }));
        } else if (event.type === "sources") {
          const sources = event.sources;
          updateMessage(assistantId, { sources });
        } else if (event.type === "token") {
          const text = event.text;
          updateMessage(assistantId, (m) => ({ content: m.content + text }));
        } else if (event.type === "authorization_required") {
          updateMessage(assistantId, { status: "pending-auth", authPreview: event.preview, requestBody: body });
        } else if (event.type === "error") {
          onLogoState("error");
          updateMessage(assistantId, { status: "error", error: event.message });
        } else if (event.type === "done") {
          const doneInfo: DoneInfo = event;
          updateMessage(assistantId, (m) => (m.status === "pending-auth" ? {} : { status: "done", done: doneInfo }));
          onLogoState("idle");
        }
      }
    } catch (err) {
      if (controller.signal.aborted) {
        updateMessage(assistantId, { status: "cancelled" });
        onLogoState("idle");
      } else {
        onLogoState("error");
        const message = err instanceof ApiError ? err.message : "Error de conexión con Alice.";
        updateMessage(assistantId, { status: "error", error: message });
      }
    } finally {
      setSending(false);
      abortRef.current = null;
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: text,
      privacy,
      status: "done",
      tools: [],
    };
    const history = buildHistory(messages);
    const body: ChatRequest = {
      message: text,
      privacy,
      history,
      document_ids: attachedIds,
      ...(routeOverride ? { force_route: routeOverride } : {}),
    };
    const assistantMsg: ChatMessage = {
      id: newId(),
      role: "assistant",
      content: "",
      privacy,
      status: "streaming",
      tools: [],
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    await runStream(assistantMsg.id, body);
  }

  function handleCancel() {
    abortRef.current?.abort();
  }

  function handleTextareaKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  function toggleAttachment(id: string) {
    setAttachedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  const pendingAuth = messages.find((m) => m.status === "pending-auth" && m.authPreview);

  async function handleAuthorizeOnce() {
    if (!pendingAuth?.authPreview || !pendingAuth.requestBody) return;
    const ticketId = pendingAuth.authPreview.ticket_request_id;
    const id = pendingAuth.id;
    setAuthBusy(true);
    try {
      await apiSend(`/api/egress/${ticketId}/approve`, "POST");
    } catch {
      updateMessage(id, { status: "error", error: "No se pudo autorizar la solicitud." });
      setAuthBusy(false);
      return;
    }
    const body: ChatRequest = { ...pendingAuth.requestBody, authorization_ticket: ticketId };
    updateMessage(id, {
      content: "",
      tools: [],
      sources: undefined,
      decision: undefined,
      raisedBy: undefined,
      authPreview: undefined,
      status: "streaming",
    });
    setAuthBusy(false);
    await runStream(id, body);
  }

  async function handleContinueLocal() {
    if (!pendingAuth?.requestBody) return;
    const id = pendingAuth.id;
    const body: ChatRequest = { ...pendingAuth.requestBody, force_route: "LOCAL_SIMPLE", authorization_ticket: undefined };
    updateMessage(id, {
      content: "",
      tools: [],
      sources: undefined,
      decision: undefined,
      raisedBy: undefined,
      authPreview: undefined,
      status: "streaming",
    });
    await runStream(id, body);
  }

  function handleCancelAuth() {
    if (!pendingAuth) return;
    updateMessage(pendingAuth.id, { status: "cancelled", authPreview: undefined });
  }

  const readyDocuments = documents.filter((d) => d.status === "ready");

  return (
    <div className="chat">
      <div className="chat__messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="chat__empty">
            <p>Prueba alguna de estas preguntas:</p>
            <div className="chat__examples">
              {EXAMPLE_PROMPTS.map((p) => (
                <button key={p} type="button" className="chip chip--example" onClick={() => setInput(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onCancel={handleCancel}
            onToggleDetails={() => updateMessage(m.id, { showDetails: !m.showDetails })}
          />
        ))}
      </div>

      <form
        className="chat__composer"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSend();
        }}
      >
        <div className="chat__attachments">
          {readyDocuments.length === 0 ? (
            <span className="chat__hint">No hay documentos listos para adjuntar.</span>
          ) : (
            readyDocuments.map((doc) => (
              <button
                key={doc.document_id}
                type="button"
                className={`chip${attachedIds.includes(doc.document_id) ? " chip--active" : ""}`}
                onClick={() => toggleAttachment(doc.document_id)}
                aria-pressed={attachedIds.includes(doc.document_id)}
              >
                {doc.original_name}
              </button>
            ))
          )}
        </div>

        <label htmlFor="chat-input" className="sr-only">
          Mensaje
        </label>
        <textarea
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleTextareaKeyDown}
          placeholder="Escribe tu mensaje… (Enter envía, Shift+Enter salto de línea)"
          rows={3}
        />

        <div className="chat__controls">
          <div className="chat__field">
            <label htmlFor="privacy-select">Privacidad</label>
            <select id="privacy-select" value={privacy} onChange={(e) => setPrivacy(e.target.value as Privacy)}>
              <option value="PRIVATE">PRIVATE</option>
              <option value="INTERNAL">INTERNAL</option>
              <option value="PUBLIC">PUBLIC</option>
            </select>
            <span className="chat__hint">PRIVATE nunca sale del equipo sin tu autorización.</span>
          </div>

          <div className="chat__field">
            <label htmlFor="route-select">Ruta</label>
            <select id="route-select" value={routeOverride} onChange={(e) => setRouteOverride(e.target.value as Route | "")}>
              <option value="">Automática</option>
              {ROUTES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          <div className="chat__actions">
            {sending ? (
              <button type="button" className="btn btn--danger" onClick={handleCancel}>
                Cancelar
              </button>
            ) : (
              <button type="submit" className="btn btn--primary" disabled={!input.trim()}>
                Enviar
              </button>
            )}
          </div>
        </div>
      </form>

      {pendingAuth?.authPreview && (
        <AuthorizationModal
          preview={pendingAuth.authPreview}
          busy={authBusy}
          onAuthorizeOnce={() => void handleAuthorizeOnce()}
          onContinueLocal={() => void handleContinueLocal()}
          onCancel={handleCancelAuth}
        />
      )}
    </div>
  );
}

function MessageBubble({
  message,
  onCancel,
  onToggleDetails,
}: {
  message: ChatMessage;
  onCancel: () => void;
  onToggleDetails: () => void;
}) {
  const isUser = message.role === "user";
  return (
    <div className={`bubble bubble--${message.role}`}>
      <div className="bubble__content">
        {isUser ? <p>{message.content}</p> : <Markdown text={message.content || (message.status === "streaming" ? "…" : "")} />}
      </div>

      {message.raisedBy && message.raisedBy.length > 0 && (
        <div className="bubble__notice">Privacidad elevada por: {message.raisedBy.join(", ")}</div>
      )}

      {message.status === "streaming" && (
        <button type="button" className="btn btn--ghost" onClick={onCancel}>
          Cancelar
        </button>
      )}
      {message.status === "cancelled" && <div className="bubble__notice">Mensaje cancelado.</div>}
      {message.status === "error" && <div className="bubble__notice bubble__notice--error">{message.error}</div>}

      {!isUser && (message.decision || message.done) && (
        <div className="bubble__footer">
          <button type="button" className="btn btn--link" onClick={onToggleDetails}>
            {message.showDetails ? "Ocultar detalles" : "Detalles"}
          </button>
          {message.showDetails && (
            <div className="bubble__details">
              {message.decision && (
                <>
                  <div>
                    <strong>Ruta:</strong> {message.decision.route}
                  </div>
                  <div>
                    <strong>Decidido por:</strong> {message.decision.decided_by}
                  </div>
                  <div>
                    <strong>Razón:</strong> {message.decision.reason}
                  </div>
                  <div>
                    <strong>Confianza:</strong>{" "}
                    {message.decision.confidence !== null ? `${Math.round(message.decision.confidence * 100)}%` : "regla"}
                  </div>
                  <div>
                    <strong>Privacidad:</strong> {message.decision.privacy}
                  </div>
                </>
              )}
              {message.done && (
                <>
                  <div>
                    <strong>Proveedor:</strong> {message.done.provider}
                  </div>
                  <div>
                    <strong>Modelo:</strong> {message.done.model}
                  </div>
                  <div>
                    <strong>Latencia:</strong> {message.done.latency_s.toFixed(2)} s
                  </div>
                  <div>
                    <strong>Costo:</strong> {formatCost(message.done)}
                  </div>
                </>
              )}
              {message.tools.length > 0 && (
                <div>
                  <strong>Herramientas:</strong>
                  <ul>
                    {message.tools.map((t, idx) => (
                      <li key={idx}>
                        {t.name}: {t.summary}
                        {t.sql && (
                          <pre>
                            <code>{t.sql}</code>
                          </pre>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {message.sources && message.sources.length > 0 && (
                <div>
                  <strong>Fuentes:</strong>
                  <ul>
                    {message.sources.map((s, idx) => (
                      <li key={idx}>
                        {s.url ? (
                          <a href={s.url} target={s.kind === "web" ? "_blank" : undefined} rel="noopener noreferrer">
                            {s.title}
                          </a>
                        ) : (
                          s.title
                        )}{" "}
                        ({s.kind}, {s.privacy}, {s.verification})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
