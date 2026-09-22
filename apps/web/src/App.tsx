import { ErrorBoundary } from "./components/ErrorBoundary";
import { useEffect, useState } from "react";
import { apiGet, apiSend, setCsrfToken, setUnauthorizedHandler } from "./api";
import { Nav, type Screen } from "./components/Nav";
import { Login } from "./screens/Login";
import { Chat } from "./screens/Chat";
import { Knowledge } from "./screens/Knowledge";
import { Observability } from "./screens/Observability";
import { Models } from "./screens/Models";
import { System } from "./screens/System";
import { Settings } from "./screens/Settings";
import type { LogoState } from "./types";

type AuthState = "checking" | "authenticated" | "unauthenticated";

export function App() {
  const [auth, setAuth] = useState<AuthState>("checking");
  const [screen, setScreen] = useState<Screen>("CHAT");
  const [logoState, setLogoState] = useState<LogoState>("idle");

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setCsrfToken(null);
      setAuth("unauthenticated");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    apiGet<{ user: unknown; csrf: string }>("/api/session")
      .then((res) => {
        setCsrfToken(res.csrf);
        setAuth("authenticated");
      })
      .catch(() => setAuth("unauthenticated"));
  }, []);

  async function handleLogout() {
    try {
      await apiSend("/api/logout", "POST");
    } catch {
      // ignore network errors on logout, we still clear local state below
    }
    setCsrfToken(null);
    setAuth("unauthenticated");
  }

  if (auth === "checking") {
    return (
      <div className="app-loading">
        <p>Cargando Alice…</p>
      </div>
    );
  }

  if (auth === "unauthenticated") {
    return (
      <Login
        onLoggedIn={(_user, csrf) => {
          setCsrfToken(csrf);
          setAuth("authenticated");
        }}
      />
    );
  }

  return (
    <div className="app">
      <Nav screen={screen} onChange={setScreen} logoState={logoState} onLogout={() => void handleLogout()} />
      <main className="app__main">
        <ErrorBoundary key={screen}>
        {screen === "CHAT" && <Chat onLogoState={setLogoState} />}
        {screen === "KNOWLEDGE" && <Knowledge />}
        {screen === "OBSERVABILITY" && <Observability />}
        {screen === "MODELS" && <Models />}
        {screen === "SYSTEM" && <System />}
        {screen === "SETTINGS" && <Settings />}
        </ErrorBoundary>
      </main>
    </div>
  );
}
