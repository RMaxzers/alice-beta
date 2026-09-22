"""Browser E2E smoke test of the real UI (installed Edge via Playwright, headless).
Runs against a TEST instance with a throwaway password (never the real one):
  ALICE_E2E_URL=http://127.0.0.1:8010 ALICE_E2E_PASSWORD=... python -m tests.e2e.ui_smoke
Screenshots -> work/e2e/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = os.environ.get("ALICE_E2E_URL", "http://127.0.0.1:8010")
PW = os.environ["ALICE_E2E_PASSWORD"]
OUT = Path(__file__).resolve().parents[2] / "work" / "e2e"
OUT.mkdir(parents=True, exist_ok=True)
results = []


def check(name, fn):
    try:
        fn()
        results.append((name, True, ""))
    except Exception as e:  # noqa: BLE001
        results.append((name, False, str(e).splitlines()[0][:200]))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_page(viewport={"width": 1366, "height": 860})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(URL)
        check("login screen", lambda: expect(page.get_by_label("Contraseña")).to_be_visible(timeout=10000))
        page.get_by_label("Usuario").fill("admin")
        page.get_by_label("Contraseña").fill("wrong")
        page.locator("button[type=submit]").click()
        check("bad password rejected", lambda: expect(page.get_by_role("alert")).to_contain_text("incorrectos", timeout=5000))
        page.get_by_label("Contraseña").fill(PW)
        page.locator("button[type=submit]").click()
        check("chat visible after login", lambda: expect(page.locator("#chat-input")).to_be_visible(timeout=10000))
        page.screenshot(path=str(OUT / "01-chat-empty.png"))

        def ask(text):
            page.locator("#chat-input").fill(text)
            page.locator("#chat-input").press("Enter")

        ask("¿Cómo está Alice?")
        check("observability answer streamed", lambda: expect(page.get_by_text("health check", exact=False).first).to_be_visible(timeout=30000))
        page.get_by_role("button", name="Detalles").last.click()
        check("details show route", lambda: expect(page.get_by_text("Ruta:").last.locator("..")).to_contain_text("OBSERVABILITY", timeout=5000))
        page.screenshot(path=str(OUT / "02-chat-observability.png"), full_page=True)

        ask("¿Cuántos activos del inventario están fuera de soporte?")
        check("SQL answer 16", lambda: expect(page.get_by_text("16", exact=False).last).to_be_visible(timeout=60000))

        # privacy: PRIVATE + forced cloud -> authorization modal
        page.locator("#route-select").select_option("CLOUD_POWERFUL")
        ask("Usa el modelo más potente: explica el principio de mínimo privilegio")
        modal = page.get_by_role("dialog")
        check("authorization modal shown", lambda: expect(modal).to_be_visible(timeout=30000))
        check("modal shows model", lambda: expect(modal.get_by_text("anthropic/claude-sonnet-5", exact=False).first).to_be_visible())
        page.screenshot(path=str(OUT / "03-authorization-modal.png"))
        modal.get_by_role("button", name="Continuar localmente").click()
        check("continued locally", lambda: expect(modal).to_be_hidden(timeout=5000))
        page.wait_for_timeout(8000)
        page.locator("#route-select").select_option(index=0)

        for label, shot in (("Conocimiento", "04-knowledge"), ("Observabilidad", "05-observability"), ("Modelos", "06-models"),
                            ("Sistema", "07-system"), ("Ajustes", "08-settings")):
            nav = page.get_by_role("navigation").get_by_role("button", name=label, exact=False)
            if nav.count() == 0:
                nav = page.get_by_role("navigation").get_by_text(label, exact=False)
            nav.first.click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / f"{shot}.png"), full_page=True)
            check(f"{label} renders", lambda: expect(page.locator("main")).not_to_be_empty())

        mobile = b.new_page(viewport={"width": 375, "height": 760})
        mobile.goto(URL)
        mobile.wait_for_timeout(1500)
        mobile.screenshot(path=str(OUT / "09-mobile.png"))
        check("no horizontal scroll on mobile", lambda: None if mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1") else (_ for _ in ()).throw(AssertionError("horizontal overflow")))
        csp = [e for e in errors if "Content Security Policy" in e or "Refused" in e]
        check("no CSP violations / JS errors", lambda: None if not csp and not [e for e in errors if "Uncaught" in e] else (_ for _ in ()).throw(AssertionError(str(errors[:3]))))
        b.close()
    for n, ok, msg in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {n} {msg}")
    print(f"console errors: {errors[:5]}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
