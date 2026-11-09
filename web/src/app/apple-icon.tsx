import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

/** Home-screen icon: the F mark with the accent dot (a signal, surfaced). */
export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", background: "#15161A", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="120" height="120" viewBox="0 0 64 64">
          <path d="M20 46V18h22" fill="none" stroke="#F6F5F1" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M20 32h14" fill="none" stroke="#F6F5F1" strokeWidth="6" strokeLinecap="round" />
          <circle cx="45" cy="44" r="5" fill="#2B59C3" />
        </svg>
      </div>
    ),
    size,
  );
}
