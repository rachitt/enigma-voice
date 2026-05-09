"""Central plugin builders + prompt loader.

Mirrors the reference repo's `config.py` shape so the agent can be reconfigured
per-call without code changes (voice/model passed via room metadata).
"""
from __future__ import annotations

import os

import httpx
from livekit.plugins import deepgram, elevenlabs, openai

from tools.business import render_system_prompt as _render_system_prompt


DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


_EMAIL_KEYTERMS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
    "enigmalabs.dev",
    "at sign",
    "underscore",
    "dash",
    "dot",
    "hyphen",
]


def build_stt() -> deepgram.STT:
    return deepgram.STT(
        model="nova-3",
        language="en-US",
        interim_results=True,
        smart_format=True,
        endpointing_ms=25,
        punctuate=True,
        numerals=True,
        keyterms=_EMAIL_KEYTERMS,
    )


def build_llm(model: str | None = None) -> openai.LLM:
    return openai.LLM(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        model=model or os.environ["LLM_MODEL"],
        temperature=0.3,
        timeout=httpx.Timeout(30.0),
        _strict_tool_schema=False,
    )


def build_tts(voice_id: str | None = None) -> elevenlabs.TTS:
    return elevenlabs.TTS(
        voice_id=voice_id or os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
        model="eleven_flash_v2_5",
        encoding="mp3_44100_128",
    )


render_system_prompt = _render_system_prompt
