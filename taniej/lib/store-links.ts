// Outbound URL mapping per store. Each store has a base URL and a query
// shape — when the user clicks "Kup w X" we forward them there with UTM
// tracking so we can measure click-throughs in our analytics, and so any
// future affiliate platform can attribute the sale back to us.
//
// Today: most URLs are just the store's homepage (or search). Once
// affiliate accounts are registered (Carrefour PL via Awin, Auchan via
// TradeDoubler, etc.) just swap the URLs below — no code changes needed.

interface StoreLink {
  // URL we forward to. {q} is replaced with the search query (encoded).
  url: string;
  // If true the store has an actual product search; else we just deep-link
  // to the homepage.
  searchable: boolean;
}

const UTM = "utm_source=taniejkupuj&utm_medium=affiliate&utm_campaign=basket";

export const STORE_LINKS: Record<string, StoreLink> = {
  Biedronka: {
    url: `https://www.biedronka.pl/pl/oferty?${UTM}`,
    searchable: false,
  },
  Lidl: {
    // Lidl has on-site search
    url: `https://www.lidl.pl/q/query/{q}?${UTM}`,
    searchable: true,
  },
  Kaufland: {
    url: `https://www.kaufland.pl/?${UTM}`,
    searchable: false,
  },
  Aldi: {
    url: `https://www.aldi.pl/oferty?${UTM}`,
    searchable: false,
  },
  Netto: {
    url: `https://www.netto.pl/?${UTM}`,
    searchable: false,
  },
  Auchan: {
    // Auchan has product search + their affiliate program is the most active
    url: `https://www.auchan.pl/pl/search?text={q}&${UTM}`,
    searchable: true,
  },
  Carrefour: {
    // Carrefour PL — runs an Awin affiliate program
    url: `https://www.carrefour.pl/search?q={q}&${UTM}`,
    searchable: true,
  },
};

export function storeUrlFor(storeName: string, query?: string): string | null {
  const cfg = STORE_LINKS[storeName];
  if (!cfg) return null;
  if (cfg.searchable && query) {
    return cfg.url.replace("{q}", encodeURIComponent(query));
  }
  return cfg.url.replace("{q}", "");
}
