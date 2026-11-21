import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { TabBar } from "@/components/TabBar";
import { Welcome } from "@/components/Welcome";
import { themeBootScript } from "@/lib/theme";
import "./globals.css";

// Self-hosted (latin, variable weight) so the build never depends on reaching Google Fonts.
const sans = localFont({ src: "./fonts/geist.woff2", variable: "--font-sans", weight: "100 900", display: "swap" });
const mono = localFont({ src: "./fonts/geist-mono.woff2", variable: "--font-mono", weight: "100 900", display: "swap" });
const display = localFont({ src: "./fonts/space-grotesk.woff2", variable: "--font-display", weight: "300 700", display: "swap" });

export const metadata: Metadata = {
  title: "FINN",
  description: "Your portfolio, filtered — and who in your network can explain it.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "FINN", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAF6EF" },
    { media: "(prefers-color-scheme: dark)", color: "#0B1020" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
      </head>
      <body className={`${sans.variable} ${mono.variable} ${display.variable} font-sans antialiased`}>
        <div className="mx-auto min-h-dvh max-w-app pb-[calc(5rem+env(safe-area-inset-bottom))]">
          {children}
        </div>
        <TabBar />
        <Welcome />
      </body>
    </html>
  );
}
