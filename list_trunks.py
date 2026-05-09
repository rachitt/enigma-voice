"""Print configured LiveKit SIP trunks."""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from livekit import api


async def _main():
    load_dotenv(override=True)
    lkapi = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        inb = await lkapi.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())
        outb = await lkapi.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())

        print("== inbound ==")
        for t in inb.items:
            print(f"  {t.sip_trunk_id}  name={t.name}  numbers={list(t.numbers)}")

        print("== outbound ==")
        for t in outb.items:
            print(f"  {t.sip_trunk_id}  name={t.name}  address={t.address}  numbers={list(t.numbers)}")
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
