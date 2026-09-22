# Roadmap (after Beta 0.1)

1. **Containers**: coordinated phase to enable WSL2 + Docker Engine (needs admin + reboot, and a stability check first given the machine's reset history). DockerAdapter is ready; then optionally cAdvisor/Alloy for historical container metrics.
2. **Stability**: investigate the Kernel-Power 41 resets (PSU/thermals/driver) before long unattended runs.
3. **Auto-start**: run components as scheduled tasks or services at logon; test unattended restart.
4. **Semantic router tuning**: gather real queries, tune thresholds or drop the tier.
5. **Hermes**: an isolated Hermes profile without terminal/code execution and with local-only auxiliaries, so the adapter can be enabled under Alice's egress policy.
6. **Formats**: DOCX, EPUB (no DRM), JSON; OCR for scanned PDFs (local).
7. **Logs**: Loki + Alloy (local only) once resources are measured.
8. **External Grafana** read-only with a scoped service account (adapter exists, disabled).
9. **Email / NotebookLM**: only via official APIs with minimal read scopes.
10. Multi-user authorization, per-dataset permissions, DNS-pinned web reader.
