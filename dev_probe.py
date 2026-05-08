"""Headless brain probe — test LLM + tool flow without audio/phone/SIP.

Usage:
  python dev_probe.py "Yeah I want to book a call"
  python dev_probe.py --interactive

Set DRY_RUN=1 to mock SMS send (default). DRY_RUN=0 sends real SMS.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)

from tools.business import render_system_prompt  # noqa: E402

DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "book_and_close_tool",
            "description": "Text booking link AND hang up. THE booking action. No args.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_tool",
            "description": "List Enigma Labs services.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_call_tool",
            "description": "End call when caller is NOT booking (declined, hostile, bye).",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
]


async def run_tool(name: str, args: dict, caller_phone: str) -> str:
    if name == "book_and_close_tool":
        if DRY_RUN:
            return (f"[DRY_RUN] SMS to {caller_phone}. NOW say: "
                    "'Sent! Keep an eye out for that text. Have a great rest of your day!' "
                    "Do not say anything else. Call ends automatically.")
        import httpx
        link = os.environ["BOOKING_LINK"]
        payload = {
            "from": os.environ["TELNYX_PHONE_NUMBER"],
            "to": caller_phone,
            "text": f"Hey, this is Aria from Enigma Labs. Grab a 15-min slot here: {link}",
            "messaging_profile_id": os.environ["TELNYX_MESSAGING_PROFILE_ID"],
        }
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                "https://api.telnyx.com/v2/messages",
                json=payload,
                headers={"Authorization": f"Bearer {os.environ['TELNYX_API_KEY']}"},
            )
            r.raise_for_status()
        return ("SMS sent. NOW say: 'Sent! Keep an eye out for that text. Have a great rest of your day!' "
                "Do not say anything else. Call ends automatically.")

    if name == "get_services_tool":
        from tools.business import get_services
        services = get_services()
        return "\n".join(f"- {s['name']}: {s['short']}" for s in services)

    if name == "end_call_tool":
        return "[CALL ENDED]"

    return f"Unknown tool: {name}"


async def chat_once(client: AsyncOpenAI, model: str, messages: list, caller_phone: str) -> tuple[str, list]:
    """Run one user-turn through the LLM, executing any tool calls. Returns (assistant_text, updated_messages)."""
    full_text = ""
    while True:
        t0 = time.time()
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            temperature=0.3,
            max_tokens=300,
        )
        ttft = time.time() - t0
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []
        content = msg.content or ""

        print(f"  [LLM {ttft*1000:.0f}ms]", end="")
        if content:
            print(f" content={content!r}", end="")
        if tool_calls:
            tc_names = [tc.function.name for tc in tool_calls]
            print(f" tools={tc_names}", end="")
        print()

        if content:
            full_text += content + " "

        # Append assistant turn
        assistant_msg: dict = {"role": "assistant", "content": content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            return full_text.strip(), messages

        for tc in tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            result = await run_tool(tc.function.name, args, caller_phone)
            print(f"  [tool {tc.function.name}] -> {result[:100]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            if tc.function.name == "end_call_tool":
                return full_text.strip() or "[ended]", messages


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="user text (omit for --interactive)")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--phone", default="+15513712428")
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL"))
    parser.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL"))
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY"))
    args = parser.parse_args()

    print(f"== probe ==  model={args.model}  base_url={args.base_url}  dry_run={DRY_RUN}")
    client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)
    system = render_system_prompt() + (
        f"\n\n## This call\nDirection: outbound.\nCaller phone: {args.phone}"
    )
    messages = [{"role": "system", "content": system}]

    # Inject the standard greeting as first assistant turn (matches agent.py session.say)
    greeting = (
        "Hi, I'm Aria from Enigma Labs. I'm an AI voice assistant - "
        "I could be the one booking your next call so you never lose a customer to voicemail again. "
        "What can I do for you today?"
    )
    messages.append({"role": "assistant", "content": greeting})
    print(f"\nAria: {greeting}")

    async def turn(user_text: str):
        print(f"\nYou: {user_text}")
        messages.append({"role": "user", "content": user_text})
        reply, _ = await chat_once(client, args.model, messages, args.phone)
        print(f"\nAria: {reply}")

    if args.interactive:
        while True:
            try:
                line = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                break
            messages.append({"role": "user", "content": line})
            reply, _ = await chat_once(client, args.model, messages, args.phone)
            print(f"\nAria: {reply}")
    else:
        if not args.input:
            print("ERROR: pass user text as arg or use --interactive")
            sys.exit(1)
        await turn(args.input)


if __name__ == "__main__":
    asyncio.run(main())
