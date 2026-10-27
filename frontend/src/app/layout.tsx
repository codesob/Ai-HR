import type { Metadata } from "next";
import { Caveat, Geist, Young_Serif } from "next/font/google";
import { AppShell } from "@/components/Nav";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const serif = Young_Serif({ subsets: ["latin"], weight: "400", variable: "--font-serif", display: "swap" });
const hand = Caveat({ subsets: ["latin"], weight: ["500", "700"], variable: "--font-caveat", display: "swap" });

export const metadata: Metadata = {
  title: "AI-HR · Simple HR for growing teams",
  description: "Read every resume, call the right five. Applicants ranked against the job with the reasons written down, plus time off, payroll and HR questions in one place.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.variable} ${serif.variable} ${hand.variable}`}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
