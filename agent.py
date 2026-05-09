import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from livekit import rtc
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
from livekit.plugins import silero

from config import build_llm, build_stt, build_tts, render_system_prompt
from tools.business import get_services
from tools.email import send_booking_email
from tools.transfer import transfer_call_tool

load_dotenv(override=True)
logger = logging.getLogger("enigma-voice")


# ---------- tools ----------

@function_tool
async def get_services_tool(ctx: RunContext) -> str:
    """List the three services Enigma Labs offers."""
    services = get_services()
    return "\n".join(f"- {s['name']}: {s['short']}" for s in services)


async def _drain_and_close(session, timeout: float = 30.0):
    """Wait until any pending TTS finishes streaming, then close the session."""
    import time
    deadline = time.time() + timeout
    await asyncio.sleep(0.4)
    while time.time() < deadline:
        speech = session.current_speech
        if speech is None or speech.done():
            break
        try:
            await speech.wait_for_playout()
        except Exception:
            await asyncio.sleep(0.2)
    await asyncio.sleep(0.6)
    try:
        await session.aclose()
    except Exception:
        logger.exception("session close failed")


def _normalize_email(raw: str) -> str:
    """Strip whitespace and common STT noise (' at ' -> '@', ' dot ' -> '.', spaces between letters)."""
    s = raw.strip().lower()
    s = s.replace(" at ", "@").replace(" dot ", ".")
    s = s.replace(" ", "")
    return s


@function_tool
async def book_with_email_tool(ctx: RunContext, email: str) -> str:
    """Email the Cal.com booking link to the caller AND end the call gracefully.

    Call this **once** when (a) the caller has agreed to book, (b) they have spoken their email,
    (c) you have spelled the email back to them letter-by-letter, and (d) they have explicitly confirmed it.
    Never call this without spell-back confirmation. After this returns, the call hangs up automatically.

    Args:
        email: The confirmed email address as a single normalized string (e.g. 'meyhar@gmail.com').
    """
    cleaned = _normalize_email(email)
    if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
        return f"Email '{cleaned}' looks invalid. Ask the caller to spell it letter-by-letter again, spell it back, get confirmation, then call this tool with the corrected value."

    ud = ctx.session.userdata or {}
    lead_name = ud.get("lead_name", "")
    logger.info("book_with_email: target=%s lead=%s", cleaned, lead_name)

    ok, detail = await send_booking_email(cleaned, lead_name)
    if not ok:
        logger.error("Resend failed: %s", detail)
        asyncio.create_task(_drain_and_close(ctx.session))
        return ("Email failed - say: 'Hmm, I'm having trouble sending the email. "
                "Please email hello@enigmalabs.dev to book. Have a great day!' Then stop talking.")

    ctx.session.userdata["caller_email"] = cleaned
    asyncio.create_task(_drain_and_close(ctx.session))
    return ("Email sent. NOW say this exact line and stop: "
            "'Sent! Keep an eye on your inbox for the booking link. Have a great rest of your day!' "
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
    voice_id = md.get("voice_id") or None
    llm_model = md.get("llm_model") or None

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
        tools=[get_services_tool, book_with_email_tool, end_call_tool, transfer_call_tool],
    )

    session = AgentSession(
        stt=build_stt(),
        llm=build_llm(llm_model),
        tts=build_tts(voice_id),
        vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
        preemptive_generation=True,
        userdata={
            "caller_phone": caller_phone,
            "caller_email": "",
            "lead_name": lead_name,
            "direction": direction,
            "sip_participant_identity": None,
        },
        conn_options=SessionConnectOptions(
            llm_conn_options=APIConnectOptions(timeout=25.0, max_retry=1),
        ),
    )

    @ctx.room.on("participant_connected")
    def _on_participant(participant: rtc.RemoteParticipant):
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            session.userdata["sip_participant_identity"] = participant.identity
            logger.info("SIP participant joined: identity=%s", participant.identity)

    for p in ctx.room.remote_participants.values():
        if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            session.userdata["sip_participant_identity"] = p.identity

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
            port=8089,
        )
    )
