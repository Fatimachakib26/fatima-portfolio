import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CRÉDIT HORIZON · Risk Intelligence",
  description: "Plateforme de gestion intelligente des risques financiers pour le financement des TPE – Projet EMSI.",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = { themeColor: "#063b2b", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
