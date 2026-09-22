import type { LogoState } from "../types";

const STATE_COLOR: Record<LogoState, string> = {
  idle: "#8b949e",
  routing: "#58a6ff",
  local: "#3fd9c7",
  knowledge: "#a371f7",
  cloud: "#d29922",
  observability: "#58a6ff",
  error: "#f85149",
};

const STATE_LABEL: Record<LogoState, string> = {
  idle: "en espera",
  routing: "enrutando",
  local: "modelo local",
  knowledge: "consultando conocimiento",
  cloud: "modelo en la nube",
  observability: "observabilidad",
  error: "error",
};

const NODES = [
  { x: 32, y: 8 },
  { x: 53, y: 20 },
  { x: 53, y: 44 },
  { x: 32, y: 56 },
  { x: 11, y: 44 },
];

export function Logo({ state = "idle", size = 40 }: { state?: LogoState; size?: number }) {
  const color = STATE_COLOR[state];
  return (
    <svg
      className={`alice-logo alice-logo--${state}`}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={`Alice: ${STATE_LABEL[state]}`}
    >
      <g stroke={color} strokeWidth="2" fill="none">
        {NODES.map((n, idx) => (
          <line
            key={idx}
            className="alice-logo__line"
            style={{ animationDelay: `${idx * 0.15}s` }}
            x1="32"
            y1="32"
            x2={n.x}
            y2={n.y}
          />
        ))}
      </g>
      <g fill={color}>
        {NODES.map((n, idx) => (
          <circle
            key={idx}
            className="alice-logo__node"
            style={{ animationDelay: `${idx * 0.15}s` }}
            cx={n.x}
            cy={n.y}
            r="3"
          />
        ))}
      </g>
      <circle className="alice-logo__core" cx="32" cy="32" r="8" fill={color} />
    </svg>
  );
}
