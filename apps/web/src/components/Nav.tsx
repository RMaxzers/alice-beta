import type { LogoState } from "../types";
import { Logo } from "./Logo";

export type Screen = "CHAT" | "KNOWLEDGE" | "OBSERVABILITY" | "MODELS" | "SYSTEM" | "SETTINGS";

const ITEMS: { id: Screen; label: string }[] = [
  { id: "CHAT", label: "Chat" },
  { id: "KNOWLEDGE", label: "Conocimiento" },
  { id: "OBSERVABILITY", label: "Observabilidad" },
  { id: "MODELS", label: "Modelos" },
  { id: "SYSTEM", label: "Sistema" },
  { id: "SETTINGS", label: "Ajustes" },
];

export function Nav({
  screen,
  onChange,
  logoState,
  onLogout,
}: {
  screen: Screen;
  onChange: (s: Screen) => void;
  logoState: LogoState;
  onLogout: () => void;
}) {
  return (
    <nav className="nav" aria-label="Navegación principal">
      <div className="nav__brand">
        <Logo state={logoState} size={32} />
        <span className="nav__title">Alice</span>
      </div>
      <ul className="nav__list">
        {ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={`nav__item${screen === item.id ? " nav__item--active" : ""}`}
              aria-current={screen === item.id ? "page" : undefined}
              onClick={() => onChange(item.id)}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="nav__logout" onClick={onLogout}>
        Cerrar sesión
      </button>
    </nav>
  );
}
