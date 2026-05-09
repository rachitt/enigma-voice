from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("enigma-voice.sms")


async def send_booking_sms(caller_phone: str) -> tuple[bool, str]:
    booking_link = os.environ.get("BOOKING_LINK", "")
    if not booking_link or not caller_phone:
        return False, "missing booking link or caller phone"
    payload = {
        "from": os.environ["TELNYX_PHONE_NUMBER"],
        "to": caller_phone,
        "text": (
            "Hey, this is Aria from Enigma Labs. Grab a 15-min slot here whenever "
            f"works for you: {booking_link}"
        ),
        "messaging_profile_id": os.environ["TELNYX_MESSAGING_PROFILE_ID"],
    }
    headers = {
        "Authorization": f"Bearer {os.environ['TELNYX_API_KEY']}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post("https://api.telnyx.com/v2/messages", json=payload, headers=headers)
    logger.info("Telnyx SMS resp: status=%d body=%s", r.status_code, r.text[:300])
    if r.status_code >= 400:
        return False, f"telnyx {r.status_code}: {r.text[:200]}"
    return True, "ok"
