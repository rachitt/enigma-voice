export type VoiceOption = { id: string; label: string };

export const VOICES: VoiceOption[] = [
  { id: "pNInz6obpgDQGcFmaJgB", label: "Adam (default)" },
  { id: "21m00Tcm4TlvDq8ikWAM", label: "Rachel" },
  { id: "AZnzlk1XvdvUeBnXmlld", label: "Domi" },
  { id: "EXAVITQu4vr4xnSDxMaL", label: "Bella" },
  { id: "ErXwobaYiN019PkySvjV", label: "Antoni" },
  { id: "MF3mGyEYCl7XYWbV9V6O", label: "Elli" },
  { id: "TxGEqnHWrfWFTfGW9XjX", label: "Josh" },
  { id: "VR6AewLTigWG4xSOukaG", label: "Arnold" },
];

export type LlmOption = { id: string; label: string };

export const LLMS: LlmOption[] = [
  { id: "", label: "Default (.env LLM_MODEL)" },
  { id: "moonshotai/kimi-k2.6", label: "Kimi K2.6 (fastest)" },
  { id: "nvidia/nemotron-3-nano-30b-a3b", label: "Nemotron 3 Nano 30B" },
  { id: "moonshotai/kimi-k2-instruct", label: "Kimi K2 Instruct" },
];
