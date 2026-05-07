from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_ROOT = Path(__file__).resolve().parents[1]
_BUSINESS_PATH = _ROOT / "business.yaml"
_SYSTEM_PROMPT_PATH = _ROOT / "prompts" / "system.md"


def _load_business_facts() -> dict[str, Any]:
    with _BUSINESS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{_BUSINESS_PATH} must contain a YAML mapping")
    return data


_BUSINESS_FACTS = _load_business_facts()


def get_services() -> list[dict]:
    """Returns [{name, short, desc}, ...] for all 3 services."""
    services = _BUSINESS_FACTS.get("services", [])
    return [
        {"name": service.get("name"), "short": service.get("short"), "desc": service.get("desc")}
        for service in services
    ]


def get_objection_response(key: str) -> str | None:
    """Lookup by key from business.yaml objection_responses."""
    responses = _BUSINESS_FACTS.get("objection_responses", {})
    if not isinstance(responses, dict):
        return None
    value = responses.get(key)
    return value if isinstance(value, str) else None


def get_business_facts() -> dict:
    """Full loaded yaml as dict."""
    return _BUSINESS_FACTS


def render_system_prompt() -> str:
    """Render prompts/system.md with static business.yaml placeholders."""
    prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    services = "\n".join(
        f"- {service['name']}: {service['short']} - {service['desc']}" for service in get_services()
    )
    differentiators = "\n".join(f"- {item}" for item in _BUSINESS_FACTS.get("differentiators", []))

    replacements = {
        "{{POSITIONING}}": str(_BUSINESS_FACTS.get("positioning", "")),
        "{{SERVICE_LIST}}": services,
        "{{DIFFERENTIATORS}}": differentiators,
        "{{TONE}}": str(_BUSINESS_FACTS.get("tone", "")),
    }
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt
