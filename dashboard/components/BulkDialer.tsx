"use client";

import { useState } from "react";

const fieldStyle: React.CSSProperties = {
  width: "100%",
  padding: 8,
  background: "#171717",
  color: "#f5f5f5",
  border: "1px solid #262626",
  borderRadius: 4,
  fontFamily: "ui-monospace, monospace",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 16px",
  background: "#fff",
  color: "#0a0a0a",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
  marginTop: 16,
};

type Lead = { phone: string; name: string; context: string; voice_id?: string; llm_model?: string };

function parseCsv(text: string): Lead[] {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length === 0) return [];
  const header = lines[0].split(",").map((h) => h.trim());
  const rows = lines.slice(1).filter((l) => l.trim());
  return rows.map((row) => {
    const cells = row.split(",").map((c) => c.trim());
    const obj: Record<string, string> = {};
    header.forEach((h, i) => (obj[h] = cells[i] ?? ""));
    const lead: Lead = {
      phone: obj.phone || "",
      name: obj.name || "",
      context: obj.context || "",
    };
    if (obj.voice_id) lead.voice_id = obj.voice_id;
    if (obj.llm_model) lead.llm_model = obj.llm_model;
    return lead;
  });
}

export function BulkDialer() {
  const [csv, setCsv] = useState("phone,name,context\n+15551234567,Jane,asked about workflows\n");
  const [throttle, setThrottle] = useState(1500);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    const leads = parseCsv(csv).filter((l) => l.phone);
    try {
      const r = await fetch("/api/bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ leads, throttle_ms: throttle }),
      });
      setResult(JSON.stringify(await r.json(), null, 2));
    } catch (err) {
      setResult(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h1 style={{ marginTop: 0 }}>Bulk dial</h1>
      <p style={{ color: "#a3a3a3", marginTop: 0 }}>
        CSV columns: <code>phone,name,context[,voice_id,llm_model]</code>
      </p>
      <textarea style={{ ...fieldStyle, minHeight: 200 }} value={csv} onChange={(e) => setCsv(e.target.value)} />
      <label style={{ display: "block", marginTop: 12 }}>
        Throttle (ms between dials)
        <input
          type="number"
          min={0}
          step={100}
          value={throttle}
          onChange={(e) => setThrottle(parseInt(e.target.value || "0", 10))}
          style={fieldStyle}
        />
      </label>
      <button type="submit" disabled={busy} style={buttonStyle}>
        {busy ? "Queueing…" : "Queue batch"}
      </button>
      {result && (
        <pre style={{ marginTop: 16, background: "#171717", padding: 12, borderRadius: 4, overflow: "auto" }}>
          {result}
        </pre>
      )}
    </form>
  );
}
