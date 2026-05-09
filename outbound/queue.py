"""In-memory bulk-dial queue.

Sequential worker that dispatches outbound calls with a configurable throttle.
Per-call exceptions are isolated and logged so one bad number doesn't block the rest.

Not durable — restart loses the queue. Swap for Redis/RQ when traffic warrants.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass

from livekit import api

logger = logging.getLogger("enigma-voice.queue")


@dataclass
class Lead:
    phone: str
    name: str
    context: str = ""
    voice_id: str | None = None
    llm_model: str | None = None


_QUEUE: asyncio.Queue[tuple[str, Lead, float]] = asyncio.Queue()
_WORKER_TASK: asyncio.Task | None = None


async def _dial_one(lead: Lead) -> dict:
    lkapi = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        room_name = f"outbound-{uuid.uuid4().hex[:8]}"
        md_dict: dict = {
            "direction": "outbound",
            "lead_name": lead.name,
            "context": lead.context,
        }
        if lead.voice_id:
            md_dict["voice_id"] = lead.voice_id
        if lead.llm_model:
            md_dict["llm_model"] = lead.llm_model
        metadata = json.dumps(md_dict)

        await lkapi.room.create_room(api.CreateRoomRequest(name=room_name, metadata=metadata))
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name="enigma-voice",
                room=room_name,
                metadata=metadata,
            )
        )
        await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=os.environ["SIP_OUTBOUND_TRUNK_ID"],
                sip_call_to=lead.phone,
                room_name=room_name,
                participant_identity=f"caller-{uuid.uuid4().hex[:6]}",
                participant_name=lead.name,
            )
        )
        return {"room": room_name, "phone": lead.phone, "status": "dialing"}
    finally:
        await lkapi.aclose()


async def _worker():
    while True:
        batch_id, lead, throttle_s = await _QUEUE.get()
        try:
            result = await _dial_one(lead)
            logger.info("bulk dial ok batch=%s phone=%s room=%s", batch_id, lead.phone, result["room"])
        except Exception:
            logger.exception("bulk dial failed batch=%s phone=%s", batch_id, lead.phone)
        finally:
            _QUEUE.task_done()
        await asyncio.sleep(throttle_s)


def ensure_worker_started():
    global _WORKER_TASK
    if _WORKER_TASK is None or _WORKER_TASK.done():
        _WORKER_TASK = asyncio.create_task(_worker())


async def enqueue(leads: list[Lead], throttle_ms: int = 1500) -> str:
    ensure_worker_started()
    batch_id = uuid.uuid4().hex[:10]
    throttle_s = max(0, throttle_ms) / 1000.0
    for lead in leads:
        await _QUEUE.put((batch_id, lead, throttle_s))
    return batch_id
