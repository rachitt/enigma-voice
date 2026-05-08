import asyncio
import json
import logging
import os

import httpx
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    APIConnectOptions,
    JobContext,
    RoomInputOptions,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.plugins import deepgram, elevenlabs, openai, silero

from tools.business import get_services, render_system_prompt

load_dotenv(override=True)
logger = logging.getLogger("enigma-voice")


# ---------- tools ----------

@function_tool
async def get_services_tool(ctx: RunContext) -> str:
    """List the three services Enigma Labs offers."""
    services = get_services()
    return "\n".join(f"- {s['name']}: {s['short']}" for s in services)


async def _send_sms(caller_phone: str) -> tuple[bool, str]:
    booking_link = os.environ.get("BOOKING_LINK", "")
    if not booking_link or not caller_phone:
        return False, "missing booking link or caller phone"
    payload = {
        "from": os.environ["TELNYX_PHONE_NUMBER"],
        "to": caller_phone,
        "text": f"Hey, this is Aria from Enigma Labs. Grab a 15-min slot here whenever works for you: {booking_link}",
        "messaging_profile_id": os.environ["TELNYX_MESSAGING_PROFILE_ID"],
    }
    headers = {"Authorization": f"Bearer {os.environ['TELNYX_API_KEY']}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post("https://api.telnyx.com/v2/messages", json=payload, headers=headers)
    logger.info("Telnyx SMS resp: status=%d body=%s", r.status_code, r.text[:300])
    if r.status_code >= 400:
        return False, f"telnyx {r.status_code}: {r.text[:200]}"
    return True, "ok"


async def _drain_and_close(session, timeout: float = 30.0):
    """Wait until any pending TTS finishes streaming, then close the session."""
    import time
    deadline = time.time() + timeout
    # Give the LLM a beat to start generating its closing turn.
    await asyncio.sleep(0.4)
    while time.time() < deadline:
        speech = session.current_speech
        if speech is None or speech.done():
            break
        try:
            await speech.wait_for_playout()
        except Exception:
            await asyncio.sleep(0.2)
    # Extra drain for SIP audio buffer.
    await asyncio.sleep(0.6)
    try:
        await session.aclose()
    except Exception:
        logger.exception("session close failed")


@function_tool
async def book_and_close_tool(ctx: RunContext) -> str:
    """Use this whenever the caller agrees to book — texts the Cal.com link to their phone AND ends the call gracefully.
    This is the ONLY booking action. Never call any other tool to book. After this returns, the call will hang up automatically."""
    caller_phone = ctx.session.userdata.get("caller_phone") if ctx.session.userdata else ""
    logger.info("book_and_close: target=%r", caller_phone)

    ok, detail = await _send_sms(caller_phone)
    if not ok:
        logger.error("SMS failed: %s", detail)
        asyncio.create_task(_drain_and_close(ctx.session))
        return ("SMS failed - say: 'Hmm, I'm having trouble texting you. Please email hello@enigmalabs.dev to book. "
                "Have a great day!' Then stop talking.")

    asyncio.create_task(_drain_and_close(ctx.session))
    return ("SMS sent. NOW say this exact line and stop: "
            "'Sent! Keep an eye out for that text. Have a great rest of your day!' "
            "Do not say anything else. The call hangs up automatically after.")


@function_tool
async def end_call_tool(ctx: RunContext, reason: str = "done") -> str:
    """Hang up gracefully when the caller is NOT booking (rejection, hostile, wrong number, said bye). Never call this for a booking — use book_and_close_tool instead."""
    logger.info("end_call requested: %s", reason)
    asyncio.create_task(_drain_and_close(ctx.session))
    return "Say a short polite goodbye and stop. Call ending."


# ---------- entrypoint ----------

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    raw_md = ctx.job.metadata or ctx.room.metadata or ""
    md: dict = {}
    if raw_md:
        try:
            md = json.loads(raw_md)
        except Exception:
            logger.exception("failed to parse metadata raw=%r", raw_md)
    logger.info("entrypoint metadata: %s", md)

    direction = md.get("direction", "inbound")
    lead_name = md.get("lead_name", "")
    context_brief = md.get("context", "")
    caller_phone = md.get("phone", "")

    system = render_system_prompt()
    call_block = "\n\n## This call\n"
    call_block += f"Direction: {direction}.\n"
    if lead_name:
        call_block += f"Lead name: {lead_name}.\n"
    if context_brief:
        call_block += f"Their context: {context_brief}.\n"
    if caller_phone:
        call_block += f"Caller phone (will be auto-used by send_booking_link_tool): {caller_phone}\n"
    system += call_block

    agent = Agent(
        instructions=system,
        tools=[get_services_tool, book_and_close_tool, end_call_tool],
    )

    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="en-US",
            interim_results=True,
            smart_format=True,
            endpointing_ms=25,
            punctuate=True,
        ),
        llm=openai.LLM(
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            model=os.environ["LLM_MODEL"],
            temperature=0.3,
            timeout=httpx.Timeout(30.0),
            _strict_tool_schema=False,
        ),
        tts=elevenlabs.TTS(
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            model="eleven_flash_v2_5",
            encoding="pcm_16000",
        ),
        vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
        preemptive_generation=True,
        userdata={"caller_phone": caller_phone, "lead_name": lead_name, "direction": direction},
        conn_options=SessionConnectOptions(
            llm_conn_options=APIConnectOptions(timeout=25.0, max_retry=1),
        ),
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(close_on_disconnect=True),
    )

    opening = (
        "Hi, I'm Aria from Enigma Labs. I'm an AI voice assistant - "
        "I could be the one booking your next call so you never lose a customer to voicemail again."
    )
    if direction == "outbound" and context_brief:
        opening += f" You'd reached out about {context_brief}."
    opening += " What can I do for you today?"
    await session.say(opening, allow_interruptions=True)


# ---------- worker ----------

def prewarm(proc):
    proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="enigma-voice",
            prewarm_fnc=prewarm,
            num_idle_processes=1,
        )
    )
