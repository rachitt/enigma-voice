"use client";

import { useState } from "react";
import { VoicePicker } from "./VoicePicker";
import { VOICES } from "../lib/voices";

const fieldStyle: React.CSSProperties = {
  width: "100%",
  padding: 8,
  background: "#171717",
  color: "#f5f5f5",
  border: "1px solid #262626",
  borderRadius: 4,
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

export function CallDispatcher() {
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [context, setContext] = useState("");
  const [voiceId, setVoiceId] = useState(VOICES[0].id);
  const [llmModel, setLlmModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const r = await fetch("/api/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, name, context, voice_id: voiceId, llm_model: llmModel || undefined }),
      });
      const json = await r.json();
      setResult(JSON.stringify(json, null, 2));
    } catch (err) {
      setResult(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h1 style={{ marginTop: 0 }}>Single call</h1>
      <label style={{ display: "block", marginTop: 12 }}>
        Phone (E.164)
        <input style={fieldStyle} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+15551234567" required />
      </label>
      <label style={{ display: "block", marginTop: 12 }}>
        Name
        <input style={fieldStyle} value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label style={{ display: "block", marginTop: 12 }}>
        Context
        <textarea style={{ ...fieldStyle, minHeight: 60 }} value={context} onChange={(e) => setContext(e.target.value)} />
      </label>
      <VoicePicker
        voiceId={voiceId}
        llmModel={llmModel}
        onVoiceChange={setVoiceId}
        onLlmChange={setLlmModel}
      />
      <button type="submit" disabled={busy} style={buttonStyle}>
        {busy ? "Dialing…" : "Dispatch"}
      </button>
      {result && (
        <pre style={{ marginTop: 16, background: "#171717", padding: 12, borderRadius: 4, overflow: "auto" }}>
          {result}
        </pre>
      )}
    </form>
  );
}
