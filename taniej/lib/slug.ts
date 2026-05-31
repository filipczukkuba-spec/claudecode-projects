// Deterministic, URL-safe slugs derived from a product name. Used for the
// programmatic SEO product pages at /cena/[slug]. No slug column in the DB —
// we slugify product.name on the fly and resolve a slug back to a product by
// slugifying every product name and matching. Product names are unique
// (uniq_products_name_lower), so slugs are effectively unique too.

const PL_MAP: Record<string, string> = {
  ą: "a", ć: "c", ę: "e", ł: "l", ń: "n", ó: "o", ś: "s", ź: "z", ż: "z",
};

export function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[ąćęłńóśźż]/g, (c) => PL_MAP[c] ?? c)
    // strip any remaining diacritics (é, ü, …)
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
