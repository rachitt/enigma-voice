from __future__ import annotations

import logging
import os

from livekit import api
from livekit.agents import RunContext, function_tool

logger = logging.getLogger("enigma-voice.transfer")


@function_tool
async def transfer_call_tool(ctx: RunContext, reason: str = "caller asked for human") -> str:
    """Transfer the live call to a human owner via SIP REFER.

    Use ONLY when the caller explicitly asks to speak to a human, owner, or wants to
    escalate. NEVER use this for booking — use book_and_close_tool for that.

    Args:
        reason: One short phrase describing why a human is needed (logged for audit).
    """
    target = os.environ.get("TRANSFER_DESTINATION", "")
    if not target:
        logger.error("transfer_call_tool: TRANSFER_DESTINATION not set")
        return "Say: 'Sorry, I can't transfer right now. Please email hello@enigmalabs.dev.' Then call end_call_tool."

    sip_identity = (
        ctx.session.userdata.get("sip_participant_identity") if ctx.session.userdata else None
    )
    if not sip_identity:
        logger.error("transfer_call_tool: no sip_participant_identity in userdata")
        return "Say: 'I'm having trouble transferring. Please email hello@enigmalabs.dev.' Then call end_call_tool."

    transfer_to = target if target.startswith("sip:") or target.startswith("tel:") else f"tel:{target}"

    lkapi = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        await lkapi.sip.transfer_sip_participant(
            api.TransferSIPParticipantRequest(
                participant_identity=sip_identity,
                room_name=ctx.room.name,
                transfer_to=transfer_to,
                play_dialtone=True,
            )
        )
    except Exception as e:
        logger.exception("SIP REFER failed: %s", e)
        return "Say: 'The transfer failed. Please email hello@enigmalabs.dev.' Then call end_call_tool."
    finally:
        await lkapi.aclose()

    logger.info("transfer initiated: reason=%r target=%s", reason, transfer_to)
    return "Say: 'Connecting you now — one moment.' Then stop talking."
