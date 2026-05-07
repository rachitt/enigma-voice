from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from livekit import api
import json
import os
import uuid


app = FastAPI(title="enigma-voice outbound trigger")


class OutboundReq(BaseModel):
    phone: str
    name: str
    context: str = ""


def _check_key(x_api_key: str | None):
    expected = os.environ["OUTBOUND_API_KEY"]
    if x_api_key != expected:
        raise HTTPException(401, "bad api key")


@app.post("/calls/outbound")
async def outbound(req: OutboundReq, x_api_key: str = Header(None)):
    _check_key(x_api_key)
    lkapi = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    room_name = f"outbound-{uuid.uuid4().hex[:8]}"
    metadata = json.dumps(
        {"direction": "outbound", "lead_name": req.name, "context": req.context}
    )

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


@app.get("/health")
def health():
    return {"ok": True}
