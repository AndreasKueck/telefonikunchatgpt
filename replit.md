# Telefon-Sprachassistent

Ein Telefon-Sprachassistent: Anrufer werden per Twilio verbunden und sprechen in Echtzeit mit einer KI (OpenAI Realtime API).

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `python3 voice-assistant/main.py` — run the voice assistant service locally (normally started by its workflow)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string
- Required secrets for the voice assistant: `OPENAI_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)
- Voice assistant: standalone Python (FastAPI + websockets), registered as a second service ("Voice Assistant") under the `api-server` artifact, served at `/voice`

## Where things live

- `voice-assistant/main.py` — the phone voice assistant (Twilio webhook + media-stream websocket bridging to OpenAI Realtime API)
- `voice-assistant/scio.txt` — auto-refreshed background knowledge file the assistant can reference during calls

## Architecture decisions

- The voice assistant is plain Python, not part of the pnpm/TypeScript workspace — it's a direct port of an existing PythonAnywhere script, kept in its own runtime to avoid a rewrite.
- It's wired in as a second `[[services]]` entry in `artifacts/api-server/.replit-artifact/artifact.toml` (path `/voice`) rather than as a new artifact, since no artifact type matches "Python backend service".
- The old ngrok/PythonAnywhere-specific logic was removed — Replit already provides a public HTTPS/WSS domain, so Twilio can call the `/voice/incoming-call` and `/voice/media-stream` endpoints directly.
- The periodic "scio.txt" background-data refresh (previously a separate cron script) now runs as an in-process asyncio background task.

## Product

- Callers dial a Twilio phone number, which is configured to hit this app's `/voice/incoming-call` webhook.
- The app opens a live audio bridge between the caller and OpenAI's Realtime API so they can have a natural spoken conversation with the AI.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Twilio's webhook URL must be updated in the Twilio console (Phone Numbers → your number → Voice → "A call comes in") to point at `https://<your-repl-domain>/voice/incoming-call`. This must be done manually — it's not automated from the code.
- The voice assistant's system prompt is currently German-language and general-purpose; the original script was Esperanto-specific with a "scio.txt" news/weather feed pointed at a specific gist URL, which returns 404 now — replace `SCIO_SOURCE_URL` if that background-data feature is wanted.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
