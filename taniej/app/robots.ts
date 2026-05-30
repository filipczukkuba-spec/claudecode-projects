import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: ["/admin", "/api/admin", "/api/track", "/go/"] },
    ],
    sitemap: "https://taniejkupuj.pl/sitemap.xml",
    host: "https://taniejkupuj.pl",
  };
}
