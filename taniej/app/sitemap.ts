import { MetadataRoute } from "next";

const BASE = "https://taniejkupuj.pl";
const STORES = ["biedronka", "lidl", "kaufland", "aldi", "netto", "auchan", "carrefour"];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${BASE}/`,         lastModified: now, changeFrequency: "daily", priority: 1.0 },
    { url: `${BASE}/promocje`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    ...STORES.map((s) => ({
      url: `${BASE}/promocje/${s}`,
      lastModified: now,
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
  ];
}
