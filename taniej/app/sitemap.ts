import { MetadataRoute } from "next";
import { createAdminClient } from "@/lib/supabase-admin";
import { slugify } from "@/lib/slug";

const BASE = "https://taniejkupuj.pl";
const STORES = ["biedronka", "lidl", "kaufland", "aldi", "netto", "auchan", "carrefour"];

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const admin = createAdminClient();
  const { data } = await admin.from("products").select("name");
  const productUrls: MetadataRoute.Sitemap = (data ?? []).map((p: { name: string }) => ({
    url: `${BASE}/cena/${slugify(p.name)}`,
    lastModified: now,
    changeFrequency: "daily" as const,
    priority: 0.7,
  }));

  return [
    { url: `${BASE}/`,         lastModified: now, changeFrequency: "daily", priority: 1.0 },
    { url: `${BASE}/ceny`,     lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${BASE}/promocje`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    ...STORES.map((s) => ({
      url: `${BASE}/promocje/${s}`,
      lastModified: now,
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
    ...productUrls,
  ];
}
