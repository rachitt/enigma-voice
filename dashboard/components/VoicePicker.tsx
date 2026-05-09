"use client";

import { LLMS, VOICES } from "../lib/voices";

type Props = {
  voiceId: string;
  llmModel: string;
  onVoiceChange: (v: string) => void;
  onLlmChange: (v: string) => void;
};

const fieldStyle: React.CSSProperties = {
  width: "100%",
  padding: 8,
  background: "#171717",
  color: "#f5f5f5",
  border: "1px solid #262626",
  borderRadius: 4,
};

export function VoicePicker({ voiceId, llmModel, onVoiceChange, onLlmChange }: Props) {
  return (
    <>
      <label style={{ display: "block", marginTop: 12 }}>
        Voice
        <select value={voiceId} onChange={(e) => onVoiceChange(e.target.value)} style={fieldStyle}>
          {VOICES.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label}
            </option>
          ))}
        </select>
      </label>
      <label style={{ display: "block", marginTop: 12 }}>
        LLM model
        <select value={llmModel} onChange={(e) => onLlmChange(e.target.value)} style={fieldStyle}>
          {LLMS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
