# Dashboard

NextJS app under `dashboard/`. Single-call dispatcher + bulk CSV dialer. Server-side proxies to the FastAPI outbound trigger so `OUTBOUND_API_KEY` never reaches the browser.

## Setup

```bash
cd dashboard
cp .env.example .env.local
# edit .env.local: ENIGMA_API_URL + OUTBOUND_API_KEY (must match repo .env)
npm install
npm run dev
```

Open http://localhost:3000.

## Endpoints

- `/`            single-call form (phone, name, context, voice picker, model picker)
- `/bulk`        paste CSV (`phone,name,context[,voice_id,llm_model]`), pick throttle, queue
- `/api/dispatch` server route → `POST {ENIGMA_API_URL}/calls/outbound`
- `/api/bulk`     server route → `POST {ENIGMA_API_URL}/calls/bulk`

## Run order

```bash
# shell 1
python agent.py dev

# shell 2
uvicorn outbound.server:app --port 8000

# shell 3
cd dashboard && npm run dev
```

## Voice / model lists

Edit `dashboard/lib/voices.ts` to add/remove ElevenLabs voice IDs or LLM models. Static list — no API call to ElevenLabs needed for now.

## Deploy

Vercel works out of the box; set `ENIGMA_API_URL` (publicly reachable) + `OUTBOUND_API_KEY` as project env vars. The dashboard has no auth itself — keep it behind a reverse proxy or VPN if exposed publicly.
