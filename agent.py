import json
import logging
import os

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, elevenlabs, openai, silero

from tools.business import get_services, render_system_prompt
from tools.calcom import create_booking as _book
from tools.calcom import list_available_slots as _list_slots

load_dotenv()
logger = logging.getLogger("enigma-voice")


@function_tool
async def get_services_tool(ctx: RunContext) -> str:
    """List the three services Enigma Labs offers."""
    services = get_services()
    return "\n".join(f"- {s['name']}: {s['short']}" for s in services)


@function_tool
async def list_available_slots_tool(ctx: RunContext, days_ahead: int = 5) -> str:
    """Get next available 15-minute discovery call slots. Returns 3 options for the caller."""
    slots = await _list_slots(days_ahead=days_ahead)
    top3 = slots[:3]
    if not top3:
        return "No slots available in the next %d days." % days_ahead
    return "\n".join(f"{i + 1}. {s.human} (id: {s.start_iso})" for i, s in enumerate(top3))


@function_tool
async def book_call_tool(
    ctx: RunContext,
    slot_iso: str,
    name: str,
    email: str,
    phone: str,
    company: str,
    problem: str,
) -> str:
    """Book the discovery call. slot_iso must be the exact id returned by list_available_slots_tool."""
    booking = await _book(
        slot_start_iso=slot_iso,
        name=name,
        email=email,
        phone=phone,
        company=company,
        problem=problem,
    )
    if booking.confirmed:
        return f"Booked! Confirmation will go to {email}. Booking id {booking.id}."
    return "Booking failed - please ask caller to email hello@enigmalabs.dev."


@function_tool
async def end_call_tool(ctx: RunContext, reason: str = "done") -> str:
    """Hang up the call gracefully after the farewell line. reason is for logs."""
    logger.info("end_call: %s", reason)
    await ctx.session.aclose()
    return "Call ended."


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    md = {}
    if ctx.room.metadata:
        try:
            md = json.loads(ctx.room.metadata)
        except Exception:
            logger.exception("failed to parse room metadata")

    direction = md.get("direction", "inbound")
    lead_name = md.get("lead_name", "")
    context_brief = md.get("context", "")

    system = render_system_prompt()
    if direction == "outbound" and lead_name:
        system += (
            "\n\n## This call\n"
            f"Direction: outbound. Lead name: {lead_name}. "
            f"Their inbound context: {context_brief or 'general inquiry'}."
        )
    else:
        system += "\n\n## This call\nDirection: inbound."

    agent = Agent(
        instructions=system,
        tools=[
            get_services_tool,
            list_available_slots_tool,
            book_call_tool,
            end_call_tool,
        ],
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-US"),
        llm=openai.LLM(
            base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            api_key=os.environ["NVIDIA_API_KEY"],
            model=os.environ.get("LLM_MODEL", "moonshotai/kimi-k2.6"),
            temperature=0.3,
        ),
        tts=elevenlabs.TTS(
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            model="eleven_turbo_v2_5",
        ),
        vad=silero.VAD.load(),
    )

    await session.start(agent=agent, room=ctx.room)

    if direction == "outbound" and lead_name:
        await session.generate_reply(
            instructions=(
                f"Greet the caller by name: 'Hi {lead_name}, this is Aria from Enigma Labs - "
                "got a quick minute? You'd reached out about "
                f"{context_brief or 'AI workflows'}.'"
            )
        )
    else:
        await session.generate_reply(
            instructions="Greet: 'Hi, this is Aria from Enigma Labs - how can I help today?'"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="enigma-voice"))
