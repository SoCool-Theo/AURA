import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aura Admin Panel",
  description: "System administration for Aura portfolio risk intelligence.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
