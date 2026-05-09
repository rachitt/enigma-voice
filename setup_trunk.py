"""Idempotent LiveKit SIP trunk creator/syncer for the Telnyx setup.

Replaces the manual `lk sip outbound create` step in docs/livekit-sip.md.

Reads from env:
    LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET
    TELNYX_PHONE_NUMBER (E.164, used for both inbound + outbound)
    TELNYX_SIP_USERNAME, TELNYX_SIP_PASSWORD (outbound auth)

Run:
    python setup_trunk.py
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from livekit import api


INBOUND_NAME = "enigma-voice-inbound"
OUTBOUND_NAME = "enigma-voice-outbound"
TELNYX_SIP_HOST = "sip.telnyx.com"


async def _ensure_inbound(lkapi: api.LiveKitAPI, number: str) -> str:
    existing = await lkapi.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())
    for t in existing.items:
        if t.name == INBOUND_NAME:
            print(f"inbound trunk exists: {t.sip_trunk_id} (skipping create)")
            return t.sip_trunk_id

    info = api.SIPInboundTrunkInfo(name=INBOUND_NAME, numbers=[number])
    res = await lkapi.sip.create_sip_inbound_trunk(api.CreateSIPInboundTrunkRequest(trunk=info))
    print(f"inbound trunk created: {res.sip_trunk_id}")
    return res.sip_trunk_id


async def _ensure_outbound(lkapi: api.LiveKitAPI, number: str, user: str, pw: str) -> str:
    existing = await lkapi.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())
    for t in existing.items:
        if t.name == OUTBOUND_NAME:
            print(f"outbound trunk exists: {t.sip_trunk_id} (skipping create)")
            return t.sip_trunk_id

    info = api.SIPOutboundTrunkInfo(
        name=OUTBOUND_NAME,
        address=TELNYX_SIP_HOST,
        numbers=[number],
        auth_username=user,
        auth_password=pw,
        transport=api.SIPTransport.SIP_TRANSPORT_TLS,
    )
    res = await lkapi.sip.create_sip_outbound_trunk(api.CreateSIPOutboundTrunkRequest(trunk=info))
    print(f"outbound trunk created: {res.sip_trunk_id}")
    return res.sip_trunk_id


async def _main():
    load_dotenv(override=True)
    number = os.environ["TELNYX_PHONE_NUMBER"]
    user = os.environ["TELNYX_SIP_USERNAME"]
    pw = os.environ["TELNYX_SIP_PASSWORD"]

    lkapi = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        in_id = await _ensure_inbound(lkapi, number)
        out_id = await _ensure_outbound(lkapi, number, user, pw)
        print()
        print("Add to your .env:")
        print(f"SIP_INBOUND_TRUNK_ID={in_id}")
        print(f"SIP_OUTBOUND_TRUNK_ID={out_id}")
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
