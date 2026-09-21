# AI architecture (Phase 14)

AI is an **enhancement, never the foundation**. All deterministic engines
(deadlines, recurrence, risk, search, versioning, audit) run identically with
or without AI. The app boots, processes documents, and serves every page with
no API key configured.

## Provider abstraction (`ai/`)
- `BaseProvider` protocol with `classify_clause(text) → dict | None`.
- `OpenAICompatibleProvider` — OpenAI or any compatible base URL
  (`OPENAI_BASE_URL`), JSON mode, temperature 0.
- `GeminiProvider` — Generative Language REST API, JSON response MIME.
- No extra dependencies (stdlib `urllib`); timeouts + no retries-storm
  (fail fast, fall back to rules).

## Safety rules
- Keys only from environment (`GEMINI_API_KEY` / `OPENAI_API_KEY`); never
  committed, never logged, never sent to the client.
- `validated_classification` rejects unknown types and clamps confidence to
  ≤0.95; garbage output → `None` → rule engine.
- `classify_clause_ai` **never raises** on provider failure.
- Extraction records `extraction_method`: RULE (deterministic), LLM (AI
  overrode), HYBRID (AI agreed with rules).
- AI never writes business state directly; its outputs are validated and
  enter the same NEEDS_REVIEW pipeline as rule outputs.

## Configuration
`AI_PROVIDER=none|openai|gemini`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`OPENAI_BASE_URL`, `AI_MODEL`, `AI_TIMEOUT_SECONDS` (see `.env.example`).

## Endpoints
`GET /api/v1/ai/status/` (provider + configured flag),
`POST /api/v1/ai/classify/` (`{text}` → rule result, AI result, and which was used).
