# Progress log (for resuming after context loss)

| Phase | Status | Evidence |
|---|---|---|
| 0 Inventory | done | ENVIRONMENT.md; risk found: 6 Kernel-Power 41 resets in 14 days, modified NVIDIA driver, no WSL |
| 1 Architecture decision | done | D1 native Windows (user-approved), DECISIONS.md |
| 2 Repository foundation | done | commit `chore: initialize alice workspace` |
| 3 Local inference | done | qwen3 4B 100 % GPU (`ollama ps`), bge-m3 pulled |
| 4 Routing | done | ROUTER-EVAL.md 52/52 |
| 5 Knowledge/RAG | done | DEMO-RUN steps 4, 5, 13, 14 |
| 6 Cloud providers | done | real OpenRouter calls (Sonnet 5, DeepSeek flash), real Tavily searches |
| 7 Observability | done | Prometheus targets 5/5 up, dashboard 31 panels verified |
| 8 UI | done | E2E 16/16 (tests/e2e/ui_smoke.py, Edge headless) |
| 9 Remote access | done locally; **external laptop test pending (user)** | REMOTE-DEMO.md |
| 10 Security validation | done | security tests, gitleaks clean, independent read-only review (see TEST-REPORT) |
| 11 Integration tests | done | pytest 69 passed |
| 12 Demo rehearsal | done | DEMO-RUN.md 15/15 |
| 13 Git sanitization | done | .gitignore, staged review, gitleaks |
| 14 Private repository | see STATUS.md | |

Resume commands: `scripts\windows\Start-Alice.ps1`, then `scripts\windows\Test-Alice.ps1` and `Demo-Alice.ps1`.
