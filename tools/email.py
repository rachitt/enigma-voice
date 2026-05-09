from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("enigma-voice.email")


_HTML_TMPL = """\
<div style="font-family: ui-sans-serif, system-ui, sans-serif; line-height:1.5;">
  <p>Hey{name_line},</p>
  <p>This is Aria from Enigma Labs — thanks for chatting just now.</p>
  <p>Grab a 15-minute discovery call with the team here:</p>
  <p>
    <a href="{link}" style="display:inline-block; padding:10px 16px; background:#0a0a0a; color:#fff; text-decoration:none; border-radius:4px;">
      Book your call
    </a>
  </p>
  <p>Pick whatever time works — Cal.com sends the calendar invite the moment you confirm.</p>
  <p>— Enigma Labs</p>
</div>
"""


async def send_booking_email(to_email: str, lead_name: str = "") -> tuple[bool, str]:
    api_key = os.environ.get("RESEND_API_KEY", "")
    sender = os.environ.get("RESEND_FROM", "")
    reply_to = os.environ.get("RESEND_REPLY_TO", "")
    booking_link = os.environ.get("BOOKING_LINK", "")
    if not api_key or not sender or not booking_link or not to_email:
        return False, "missing resend config or destination email"

    name_line = f" {lead_name}" if lead_name else ""
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": "Book your 15-min call with Enigma Labs",
        "html": _HTML_TMPL.format(name_line=name_line, link=booking_link),
    }
    if reply_to:
        payload["reply_to"] = reply_to

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
    logger.info("Resend resp: status=%d body=%s", r.status_code, r.text[:300])
    if r.status_code >= 400:
        return False, f"resend {r.status_code}: {r.text[:200]}"
    return True, "ok"
