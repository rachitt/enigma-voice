from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from livekit import api
from dotenv import load_dotenv
import json
import os
import uuid

load_dotenv(override=True)

from outbound.queue import Lead, enqueue


app = FastAPI(title="enigma-voice outbound trigger")


class OutboundReq(BaseModel):
    phone: str
    name: str
    context: str = ""
    voice_id: str | None = None
    llm_model: str | None = None


class BulkReq(BaseModel):
    leads: list[OutboundReq]
    throttle_ms: int = 1500


def _check_key(x_api_key: str | None):
    expected = os.environ["OUTBOUND_API_KEY"]
    if x_api_key != expected:
        raise HTTPException(401, "bad api key")


def _build_metadata(req: OutboundReq) -> str:
    md: dict = {
        "direction": "outbound",
        "lead_name": req.name,
        "context": req.context,
    }
    if req.voice_id:
        md["voice_id"] = req.voice_id
    if req.llm_model:
        md["llm_model"] = req.llm_model
    return json.dumps(md)


@app.post("/calls/outbound")
async def outbound(req: OutboundReq, x_api_key: str = Header(None)):
    _check_key(x_api_key)
    lkapi = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        room_name = f"outbound-{uuid.uuid4().hex[:8]}"
        metadata = _build_metadata(req)

        await lkapi.room.create_room(
            api.CreateRoomRequest(name=room_name, metadata=metadata)
        )
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
                sip_call_to=req.phone,
                room_name=room_name,
                participant_identity=f"caller-{uuid.uuid4().hex[:6]}",
                participant_name=req.name,
            )
        )
        return {"room": room_name, "phone": req.phone, "status": "dialing"}
    finally:
        await lkapi.aclose()


@app.post("/calls/bulk")
async def bulk(req: BulkReq, x_api_key: str = Header(None)):
    _check_key(x_api_key)
    leads = [
        Lead(
            phone=l.phone,
            name=l.name,
            context=l.context,
            voice_id=l.voice_id,
            llm_model=l.llm_model,
        )
        for l in req.leads
    ]
    batch_id = await enqueue(leads, throttle_ms=req.throttle_ms)
    return {"batch_id": batch_id, "queued": len(leads), "throttle_ms": req.throttle_ms}


@app.get("/health")
def health():
    return {"ok": True}
