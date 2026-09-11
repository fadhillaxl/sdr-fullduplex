import type { Metadata } from "next";
import { Exo, Roboto_Mono } from "next/font/google";
import "./globals.css";

const exo = Exo({
  variable: "--font-exo",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Pluto+ SDR Mesh Mission Control",
  description: "Next-gen RF Telemetry, Full-Duplex Link Controller, and Passive Antenna Analyzer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${exo.variable} ${robotoMono.variable} dark`}>
      <body className="min-h-screen bg-[#0B0B10] text-[#F8FAFC] antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
