import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "taniejkupuj — Najtańszy koszyk zakupów w Polsce",
  description: "Porównaj ceny w 7 sklepach jednocześnie: Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour. Znajdź najtańszy koszyk i oszczędzaj na zakupach.",
  manifest: "/manifest.json",
  keywords: ["porównywarka cen", "najtańsze zakupy", "biedronka lidl kaufland", "koszyk zakupów"],
  openGraph: {
    title: "taniejkupuj — Najtańszy koszyk zakupów w Polsce",
    description: "Porównaj ceny w 7 sklepach i znajdź najtańszy koszyk. Bezpłatnie.",
    url: "https://taniejkupuj.pl",
    siteName: "taniejkupuj",
    locale: "pl_PL",
    type: "website",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "taniejkupuj",
  },
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#22c55e",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl" className={`${geist.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#f0f0eb]">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
