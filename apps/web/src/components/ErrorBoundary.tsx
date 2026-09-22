import { Component, type ReactNode } from "react";

/** Keeps a crash in one screen from blanking the whole app. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null as string | null };

  static getDerivedStateFromError(e: unknown) {
    return { error: e instanceof Error ? e.message : String(e) };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="screen">
          <section className="panel" role="alert">
            <h2>Esta pantalla falló</h2>
            <p>Error: {this.state.error}. El resto de Alice sigue funcionando; cambia de pantalla o recarga.</p>
          </section>
        </div>
      );
    }
    return this.props.children;
  }
}
