from __future__ import annotations

import pytest

from tools import calcom


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    calls = []

    def __init__(self, *, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, *, params, headers):
        self.calls.append(("GET", url, params, headers, None, self.timeout))
        return FakeResponse(
            {
                "data": {
                    "2026-11-05": [
                        {"time": "2026-11-05T16:00:00Z"},
                        {"time": "2026-11-05T15:00:00Z", "end": "2026-11-05T15:15:00Z"},
                    ]
                }
            }
        )

    async def post(self, url, *, json, headers):
        self.calls.append(("POST", url, None, headers, json, self.timeout))
        return FakeResponse(
            {
                "data": {
                    "id": 123,
                    "status": "accepted",
                    "start": json["start"],
                    "attendee": {"email": json["attendee"]["email"]},
                }
            }
        )


@pytest.fixture(autouse=True)
def calcom_env(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setenv("CALCOM_API_KEY", "test-key")
    monkeypatch.setenv("CALCOM_EVENT_TYPE_ID", "42")
    monkeypatch.setenv("CALCOM_BASE_URL", "https://cal.test/v2")
    monkeypatch.setattr(calcom.httpx, "AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_list_available_slots_request_shape_and_response_parsing():
    slots = await calcom.list_available_slots(days_ahead=3, timezone="America/New_York")

    assert [slot.start_iso for slot in slots] == ["2026-11-05T15:00:00Z", "2026-11-05T16:00:00Z"]
    assert slots[0].end_iso == "2026-11-05T15:15:00Z"
    assert slots[1].end_iso == "2026-11-05T16:15:00Z"
    assert slots[0].human == "Thursday, Nov 5 at 10:00 AM EST"

    method, url, params, headers, payload, timeout = FakeAsyncClient.calls[0]
    assert method == "GET"
    assert url == "https://cal.test/v2/slots"
    assert params["eventTypeId"] == "42"
    assert params["timeZone"] == "America/New_York"
    assert "startTime" in params
    assert "endTime" in params
    assert headers == {"Authorization": "Bearer test-key", "cal-api-version": "2024-08-13"}
    assert payload is None
    assert timeout == 10.0


@pytest.mark.asyncio
async def test_create_booking_request_shape_and_response_parsing():
    booking = await calcom.create_booking(
        slot_start_iso="2026-11-05T15:00:00Z",
        name="Ada Lovelace",
        email="ada@example.com",
        phone="+15555550100",
        company="Analytical Engines",
        problem="Automate lead qualification.",
    )

    assert booking.id == "123"
    assert booking.confirmed is True
    assert booking.start_iso == "2026-11-05T15:00:00Z"
    assert booking.attendee_email == "ada@example.com"

    method, url, params, headers, payload, timeout = FakeAsyncClient.calls[0]
    assert method == "POST"
    assert url == "https://cal.test/v2/bookings"
    assert params is None
    assert headers == {"Authorization": "Bearer test-key", "cal-api-version": "2024-08-13"}
    assert payload == {
        "eventTypeId": 42,
        "start": "2026-11-05T15:00:00Z",
        "attendee": {"name": "Ada Lovelace", "email": "ada@example.com", "timeZone": "America/New_York"},
        "bookingFieldsResponses": {
            "phone": "+15555550100",
            "company": "Analytical Engines",
            "notes": "Automate lead qualification.",
        },
    }
    assert timeout == 10.0
