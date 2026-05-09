import type { ReactNode } from "react";

export const metadata = {
  title: "enigma-voice dashboard",
  description: "Dispatch Enigma Labs voice-agent calls",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          margin: 0,
          background: "#0a0a0a",
          color: "#f5f5f5",
        }}
      >
        <header style={{ padding: "16px 24px", borderBottom: "1px solid #262626" }}>
          <strong>enigma-voice</strong>{" "}
          <a href="/" style={{ color: "#a3a3a3", marginLeft: 16 }}>Single</a>{" "}
          <a href="/bulk" style={{ color: "#a3a3a3", marginLeft: 16 }}>Bulk</a>
        </header>
        <main style={{ padding: 24, maxWidth: 720, margin: "0 auto" }}>{children}</main>
      </body>
    </html>
  );
}
