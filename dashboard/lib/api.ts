const BASE = process.env.ENIGMA_API_URL ?? "http://localhost:8000";
const KEY = process.env.OUTBOUND_API_KEY ?? "";

type SingleLead = {
  phone: string;
  name: string;
  context?: string;
  voice_id?: string;
  llm_model?: string;
};

export async function dispatchSingle(lead: SingleLead) {
  const r = await fetch(`${BASE}/calls/outbound`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": KEY },
    body: JSON.stringify(lead),
    cache: "no-store",
  });
  return { ok: r.ok, status: r.status, body: await r.json().catch(() => ({})) };
}

export async function dispatchBulk(leads: SingleLead[], throttle_ms = 1500) {
  const r = await fetch(`${BASE}/calls/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": KEY },
    body: JSON.stringify({ leads, throttle_ms }),
    cache: "no-store",
  });
  return { ok: r.ok, status: r.status, body: await r.json().catch(() => ({})) };
}
