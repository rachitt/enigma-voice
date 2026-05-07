# enigma-voice

AI voice assistant for [Enigma Labs](https://enigmalabs.dev). Answers inbound calls, dials outbound leads, qualifies, and books 15-min discovery calls on Cal.com.

## Stack

- **LiveKit Agents (Python)** — agent framework, barge-in, turn detection
- **Deepgram nova-3** — STT
- **ElevenLabs** — TTS
- **NVIDIA NIM** (OpenAI-compatible) — LLM brain (Nemotron 3 Nano default; GLM-4.7 / Kimi K2 / DeepSeek V4 Flash fallbacks)
- **Twilio SIP trunk → LiveKit SIP** — telephony (inbound + outbound)
- **Cal.com API v2** — slot lookup + booking
- **FastAPI** — outbound call trigger endpoint

## Layout

```
agent.py              LiveKit worker (entrypoint)
tools/business.py     Loads business.yaml, exposes get_services
tools/calcom.py       Cal.com API client (slots, bookings)
outbound/server.py    POST /calls/outbound -> SIP dispatch
prompts/system.md     System prompt template
business.yaml         Enigma Labs facts (single source of truth)
docs/                 Twilio + LiveKit SIP setup walkthroughs
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys
```

## Run

Console mode (no phone — for fast iteration):
```bash
python agent.py console
```

Worker mode (waits for LiveKit room dispatch):
```bash
python agent.py dev
```

Outbound API:
```bash
uvicorn outbound.server:app --reload --port 8000
```

Trigger outbound call:
```bash
curl -X POST http://localhost:8000/calls/outbound \
  -H "X-API-Key: $OUTBOUND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+15555550123","name":"Jane","context":"asked about AI workflow automation"}'
```

See `docs/twilio-setup.md` and `docs/livekit-sip.md` for telephony wiring.
