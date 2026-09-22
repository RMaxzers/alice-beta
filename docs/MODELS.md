# Models (Beta 0.1)

Configured in `config/models/aliases.yaml`. Routes point to aliases; aliases point to provider + model.

## Local (Ollama 0.34.2, RTX 3070 Laptop 8 GB)
| Alias | Model | Quant | Size | Context | Placement (measured) | Notes |
|---|---|---|---|---|---|---|
| local-general, local-code, local-classifier | `qwen3:4b-instruct-2507-q4_K_M` (digest 0edcdef34593) | Q4_K_M | 2.5 GB file, 3.0–3.2 GiB loaded @4K | 4096 (classifier 2048) | 100 % GPU (`ollama ps`) | Already installed (D3). Apache-2.0 (Qwen3). Same weights for code in Beta |
| local-embedding | `bge-m3` (digest 790764642607) | F16 | 0.6 GiB loaded | 8192 | 100 % GPU | 1024-d, multilingual, MIT |

Ollama is started with `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=10m`, host 127.0.0.1.
Both models together use ≈ 3.8 GiB VRAM, leaving headroom on 8 GB.

Measured latencies (this PC, 2026-09-22):
- Cold load + first answer (LOCAL_SIMPLE, ~130 tokens): 10.8–15.8 s. Warm answers: 1.4–2.6 s for RAG/log answers (90–210 tokens); ~6 s for ~640 tokens (≈ 100 tok/s decode).
- Classifier call (ambiguous queries only): p95 ≈ 1.1 s warm; first call 16.5 s (cold load).
- GPU utilization during generation: ~90 %; VRAM 3.4 → 4.7 GiB during a long generation.

## Cloud (OpenRouter) — IDs checked against the live catalog on 2026-09-22
| Alias | Model | Price (USD / 1M tokens in/out, catalog) | max_tokens | Observed |
|---|---|---|---|---|
| cloud-cheap | `deepseek/deepseek-v4.1-flash` | 0.15 / 0.60 | 1500 | Real call OK: 247 tokens, reported USD 0.000126, **44.9 s** (slow provider on that call) |
| cloud-powerful | `anthropic/claude-sonnet-5` | 2.00 / 10.00 | 2000 | Real call OK: 162 tokens, reported USD 0.00173, 4.1 s |
| financial-research | `deepseek/deepseek-v4.1-flash` (not used: web/finance synthesis is local) | — | — | — |

Prices are read at runtime from `https://openrouter.ai/api/v1/models` (cached 1 h) to compute the max-cost reservation; they are not hard-coded.
Requests set `provider.allow_fallbacks=false`, and `data_collection="deny"` unless the payload is PUBLIC. "No training" ≠ "no retention": check OpenRouter's and the final provider's policies.

## Web search
Tavily (`TAVILY_API_KEY`, copied from Hermes' `.env` with approval). Queries are rewritten locally (qwen3) into short English keywords; the exact query is what the authorization preview shows.

## Router evaluation
See `docs/ROUTER-EVAL.md`: 52 labelled cases (40 eval-1 + 12 held-out written after rule changes). 52/52; 0 malformed classifier outputs.
Honest caveat: the semantic tier (bge-m3 similarity) decided 0 cases at current thresholds (0.62 / margin 0.04); ambiguous cases went to the classifier. It is kept because it is cheap and helps when the classifier is unavailable; thresholds can be tuned with more data.

## Future providers (not enabled)
DeepSeek direct (`DEEPSEEK_API_KEY` — a web subscription does not imply API access), Anthropic, OpenAI, Gemini: config slots only, state DISABLED / READY_FOR_CONFIGURATION. No empty implementations.
