"""CLI wrapper around the FastAPI outbound trigger.

Usage:
    python make_call.py --phone +15551234567 --name Jane --context "asked about workflow automation"
    python make_call.py --csv leads.csv --throttle-ms 2000

CSV format: phone,name,context[,voice_id[,llm_model]]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import httpx
from dotenv import load_dotenv


def _client() -> tuple[str, dict]:
    base = os.environ.get("ENIGMA_API_URL", "http://localhost:8000").rstrip("/")
    key = os.environ["OUTBOUND_API_KEY"]
    return base, {"X-API-Key": key, "Content-Type": "application/json"}


def _single(args) -> int:
    base, headers = _client()
    payload = {"phone": args.phone, "name": args.name, "context": args.context}
    if args.voice_id:
        payload["voice_id"] = args.voice_id
    if args.llm_model:
        payload["llm_model"] = args.llm_model
    r = httpx.post(f"{base}/calls/outbound", json=payload, headers=headers, timeout=30.0)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.status_code < 400 else 1


def _bulk(args) -> int:
    base, headers = _client()
    leads = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lead = {
                "phone": row["phone"].strip(),
                "name": row.get("name", "").strip(),
                "context": row.get("context", "").strip(),
            }
            if row.get("voice_id", "").strip():
                lead["voice_id"] = row["voice_id"].strip()
            if row.get("llm_model", "").strip():
                lead["llm_model"] = row["llm_model"].strip()
            leads.append(lead)
    payload = {"leads": leads, "throttle_ms": args.throttle_ms}
    r = httpx.post(f"{base}/calls/bulk", json=payload, headers=headers, timeout=30.0)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.status_code < 400 else 1


def main() -> int:
    load_dotenv(override=True)
    p = argparse.ArgumentParser(description="Trigger outbound calls via the enigma-voice FastAPI server.")
    p.add_argument("--phone", help="E.164 phone number for a single call")
    p.add_argument("--name", default="", help="Lead name")
    p.add_argument("--context", default="", help="Brief context for the agent")
    p.add_argument("--voice-id", dest="voice_id", default=None, help="ElevenLabs voice id override")
    p.add_argument("--llm-model", dest="llm_model", default=None, help="LLM model override")
    p.add_argument("--csv", help="CSV path for bulk dialing")
    p.add_argument("--throttle-ms", dest="throttle_ms", type=int, default=1500, help="Bulk throttle in ms")
    args = p.parse_args()

    if args.csv:
        return _bulk(args)
    if args.phone:
        return _single(args)
    p.error("provide --phone for single or --csv for bulk")


if __name__ == "__main__":
    sys.exit(main())
