from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx


@dataclass
class Slot:
    start_iso: str
    end_iso: str
    human: str


@dataclass
class Booking:
    id: str
    confirmed: bool
    start_iso: str
    attendee_email: str


def _settings() -> tuple[str, str, str]:
    api_key = os.environ.get("CALCOM_API_KEY")
    event_type_id = os.environ.get("CALCOM_EVENT_TYPE_ID")
    base_url = os.environ.get("CALCOM_BASE_URL", "https://api.cal.com/v2").rstrip("/")
    if not api_key:
        raise RuntimeError("CALCOM_API_KEY is required")
    if not event_type_id:
        raise RuntimeError("CALCOM_EVENT_TYPE_ID is required")
    return api_key, event_type_id, base_url


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "cal-api-version": "2024-08-13"}


def _event_type_id(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def _parse_dt(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _human(dt: datetime, timezone: str) -> str:
    local = dt.astimezone(ZoneInfo(timezone))
    return f"{local:%A}, {local:%b} {local.day} at {local:%I:%M %p %Z}".replace(" 0", " ")


def _slot_items(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        items: list[dict[str, Any]] = []
        for value in data.values():
            if isinstance(value, list):
                items.extend(item for item in value if isinstance(item, dict))
        return items
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _extract_start_end(item: dict[str, Any]) -> tuple[str | None, str | None]:
    start = item.get("start") or item.get("startTime") or item.get("time")
    end = item.get("end") or item.get("endTime")
    return start, end


async def list_available_slots(days_ahead: int = 5, timezone: str = "America/New_York") -> list[Slot]:
    """Return up to 6 available slots, sorted earliest-first."""
    api_key, event_type_id, base_url = _settings()
    now = datetime.now(UTC)
    params = {
        "eventTypeId": event_type_id,
        "startTime": _iso_utc(now),
        "endTime": _iso_utc(now + timedelta(days=days_ahead)),
        "timeZone": timezone,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/slots", params=params, headers=_headers(api_key))
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            print(f"Cal.com slots request failed with status {response.status_code}", file=sys.stderr)
            raise

    slots: list[Slot] = []
    for item in _slot_items(response.json()):
        start_raw, end_raw = _extract_start_end(item)
        if not start_raw:
            continue
        start = _parse_dt(start_raw)
        end = _parse_dt(end_raw) if end_raw else start + timedelta(minutes=15)
        slots.append(Slot(start_iso=_iso_utc(start), end_iso=_iso_utc(end), human=_human(start, timezone)))
    return sorted(slots, key=lambda slot: slot.start_iso)[:6]


async def create_booking(
    slot_start_iso: str,
    name: str,
    email: str,
    phone: str,
    company: str,
    problem: str,
    timezone: str = "America/New_York",
) -> Booking:
    """Create a Cal.com booking."""
    api_key, event_type_id, base_url = _settings()
    payload = {
        "eventTypeId": _event_type_id(event_type_id),
        "start": slot_start_iso,
        "attendee": {"name": name, "email": email, "timeZone": timezone},
        "bookingFieldsResponses": {"phone": phone, "company": company, "notes": problem},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{base_url}/bookings", json=payload, headers=_headers(api_key))
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            print(f"Cal.com booking request failed with status {response.status_code}", file=sys.stderr)
            raise

    data = response.json()
    booking = data.get("data", data) if isinstance(data, dict) else {}
    attendees = booking.get("attendees") or [{}]
    attendee = booking.get("attendee") or attendees[0] or {}
    status = str(booking.get("status", "")).lower()
    confirmed = bool(booking.get("confirmed", status in {"accepted", "confirmed"}))
    return Booking(
        id=str(booking.get("id") or booking.get("uid") or ""),
        confirmed=confirmed,
        start_iso=str(booking.get("start") or booking.get("startTime") or slot_start_iso),
        attendee_email=str(attendee.get("email") or email),
    )
