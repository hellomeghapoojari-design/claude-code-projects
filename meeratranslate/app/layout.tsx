import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MeeraTranslate — Hindi to English Book Translator",
  description: "AI-powered translation tool for psychological thriller authors",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background font-sans">{children}</body>
    </html>
  );
}
