import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "taniejkupuj.pl — Porównywarka cen 7 sklepów spożywczych",
  description: "Porównaj ceny w Biedronce, Lidlu, Kauflandzie, Aldi, Netto, Auchanie i Carrefourze. Wpisz listę zakupów, znajdź najtańszy koszyk. Bez logowania, gratis.",
  manifest: "/manifest.json",
  keywords: [
    "porównywarka cen",
    "porównywarka cen spożywczych",
    "najtańsze zakupy",
    "promocje biedronka lidl kaufland",
    "gazetka biedronki",
    "gazetka lidla",
    "koszyk zakupów online",
    "tanie zakupy",
    "porównaj ceny sklepów",
  ],
  openGraph: {
    title: "taniejkupuj.pl — Porównywarka cen 7 sklepów spożywczych",
    description: "Porównaj ceny w Biedronce, Lidlu, Kauflandzie, Aldi, Netto, Auchanie i Carrefourze. Wpisz listę zakupów, znajdź najtańszy koszyk. Bez logowania, gratis.",
    url: "https://taniejkupuj.pl",
    siteName: "taniejkupuj",
    locale: "pl_PL",
    type: "website",
    images: [
      {
        url: "https://taniejkupuj.pl/opengraph-image",
        width: 1200,
        height: 630,
        alt: "taniejkupuj — porównywarka cen w polskich sklepach spożywczych",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "taniejkupuj.pl — Porównywarka cen 7 sklepów spożywczych",
    description: "Porównaj ceny w Biedronce, Lidlu, Kauflandzie, Aldi, Netto, Auchanie i Carrefourze. Wpisz listę zakupów, znajdź najtańszy koszyk. Bez logowania, gratis.",
    images: ["https://taniejkupuj.pl/opengraph-image"],
  },
  metadataBase: new URL("https://taniejkupuj.pl"),
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
      <head>
        <meta name="convertiser-verification" content="43c8e80f84c9e5a8ab2a30e786d89e07c1cc722b" />
      </head>
      <body className="min-h-full flex flex-col bg-[#f0f0eb]">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
