# Phase 2 — WSL2 + Docker (prepared, NOT executed)

Goal: run Qdrant, Prometheus and Grafana as containers (Compose project `alice`) on Docker Engine inside a dedicated
WSL2 distro, so the Docker broker has real containers to observe. Ollama, windows_exporter, Alice API/UI and Tailscale stay on Windows.

**Why staged:** WSL2 turns on the Windows hypervisor, which needs a reboot. On this machine the hypervisor was the #2 suspect of
the earlier boot-loop, and there were 5 Kernel-Power 41 resets on 17–19 Sep (none since, including a 30-min GPU soak).
Each stage has a checkpoint and every step can be undone.

## Decisions (D18)
| Choice | Why | Rejected |
|---|---|---|
| Docker **Engine** in WSL2 | ~no extra RAM beyond the VM, no licence questions, one daemon | Docker Desktop (heavier, own VM + GUI) |
| Dedicated distro `alice-ubuntu`, imported from Canonical's official WSL image (SHA256 verified) | non-interactive install, isolated from any personal distro, VHD in `%LOCALAPPDATA%\alice-wsl` | `wsl --install -d Ubuntu` (interactive first-run user prompt) |
| `.wslconfig`: 4 GB RAM, 4 CPU, 2 GB swap, `networkingMode=mirrored`, `autoMemoryReclaim=dropCache` | 16 GB host: Windows + Ollama + browser keep headroom; mirrored keeps every port on 127.0.0.1 unchanged | default (50 % RAM, NAT) |
| Containers use `network_mode: host` + bind 127.0.0.1 | same ports as native (Alice config unchanged); Prometheus can scrape Windows 127.0.0.1:9182/9101; nothing on LAN/tailnet | Compose bridge network + published ports (would need host→Windows routing) |
| Images pinned by **digest**, same versions as native | reproducible | `latest` |
| Alice talks to Docker via `wsl.exe -d alice-ubuntu --exec docker …` (`DOCKER_CMD`) | `--exec` runs docker with no shell inside WSL → argv stays argv end to end (tested) | Docker TCP 2375 (forbidden), shell wrappers |
| Daemon on unix socket only, log rotation 10 MB×3, `live-restore` | no network API; logs can't fill the VHD | — |

## Stages
| # | Script | Admin | Reboot | What it does | Checkpoint |
|---|---|---|---|---|---|
| 1 | `Enable-WSL-Stage1.ps1` | **yes** | you, after it | refuses if nvidia-smi is broken; warns if resets in last 3 days; saves `bcdedit`/features/display state to `backups\phase2-*`; creates restore point **Pre-WSL2-Alice**; `wsl --install --no-distribution` | — |
| — | *(reboot when you choose)* | | | | |
| 2 | `Check-PostReboot.ps1` | no | — | hypervisor on; NVIDIA device OK (no Code 43); nvidia-smi; no Kernel-Power/BugCheck/TDR/WHEA since boot; **real Ollama inference 100 % GPU** + tok/s | must be all OK. Recommended: use the PC 1–3 days and re-run |
| 3 | `Install-DockerWSL.ps1` | no | — | re-runs the checkpoint; writes `.wslconfig` only if absent; imports `alice-ubuntu`; wsl.conf (systemd, user `alice`); Docker Engine + Compose from Docker's apt repo; verifies mirrored mode, docker as `alice`, no TCP listener; pulls pinned images | native services untouched |
| 4 | `Migrate-ToDocker.ps1` | no | — | backup; stops native Qdrant/Prometheus/Grafana; `compose up`; health from Windows on 127.0.0.1; **exposure scan of every LAN/tailnet IP** (auto-rollback if any port is open); restores Qdrant snapshot and checks points == SQLite chunks; sets `ALICE_RUNTIME=docker` + `DOCKER_CMD`; restarts API | any failure → automatic `Rollback-Docker.ps1` |
| 5 | `Test-Alice.ps1`, `Demo-Alice.ps1` | no | — | full suite; demo steps 6 and 9 now return real `docker stats` / `docker logs` | |

Run each with `powershell -ExecutionPolicy Bypass -File .\scripts\windows\<script>.ps1` (stage 1 from an **elevated** PowerShell).

After migration, Start/Stop/Status follow `ALICE_RUNTIME`: `Start-Alice.ps1` runs `compose up -d`, `Stop-Alice.ps1` runs `compose stop`
(never `down -v`). The Docker broker allowlist stays `alice-qdrant, alice-prometheus, alice-grafana`.

Expected cost: the WSL VM adds ~1–1.5 GB RAM while running (capped at 4 GB); disk ~2–3 GB for the distro + images.
Prometheus history restarts empty in the container (native TSDB stays on disk for rollback).

## Rollback (from least to most invasive)
1. **Back to native services** (seconds, keeps everything): `Rollback-Docker.ps1`. Docker volumes are kept. Vectors of documents ingested
   while in docker mode are only in the container volume → re-ingest them or migrate again.
2. **Hypervisor off, WSL kept** (admin + reboot): `bcdedit /set hypervisorlaunchtype off`. Undo with `bcdedit /set hypervisorlaunchtype auto`.
3. **Remove the phase** (admin): take `Backup-Alice.ps1` first, then `Rollback-Docker.ps1`, `wsl --unregister alice-ubuntu` (**deletes the distro and its volumes**),
   `dism /online /disable-feature /featurename:VirtualMachinePlatform /norestart`, `dism /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart`, reboot.
   Remove `%USERPROFILE%\.wslconfig` if it was created by stage 3.
4. **Windows doesn't boot after stage 1**: WinRE → Troubleshoot → Advanced → Command Prompt → `bcdedit /set {default} hypervisorlaunchtype off` → exit → continue.
   If that is not enough: System Restore → **Pre-WSL2-Alice**. Don't touch the NVIDIA driver or BIOS as part of this rollback.

## Validated now (without enabling anything)
- Hardware: VM monitor extensions, firmware virtualization, SLAT: **yes** (systeminfo). VT-d disabled is fine for WSL2.
- All PowerShell scripts parse; Compose file valid, host networking and digests on every service.
- Native runtime unchanged (`Start-Alice.ps1` → all HEALTHY); pytest 71 passed, incl. `test_wsl_prefix_keeps_argv_without_shell`.

## Not validated (needs the reboot)
Hypervisor stability with the modified driver, mirrored networking behaviour, container health checks and the exposure scan run
inside `Migrate-ToDocker.ps1`. Note: `App Control for Business policy: Forzado` is active on this machine; if it blocks `wsl.exe`/Docker
binaries, stage 3 will fail early without changing anything.
