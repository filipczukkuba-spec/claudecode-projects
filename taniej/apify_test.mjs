import { ApifyClient } from "apify-client";
import { readFileSync } from "fs";
const token = readFileSync(".env.local","utf8").match(/APIFY_TOKEN=(.+)/)[1].trim();
const client = new ApifyClient({ token });

const run = await client.actor("apify/website-content-crawler").call({
  startUrls: [{ url: "https://www.biedronka.pl/pl/oferty" }],
  crawlerType: "playwright:firefox",
  maxCrawlPages: 1,
  proxyConfiguration: { useApifyProxy: true, apifyProxyGroups: ["RESIDENTIAL"] },
  saveMarkdown: true,
  readableTextCharThreshold: 100,
}, { waitSecs: 180 });

console.log("status:", run.status);
const { items } = await client.dataset(run.defaultDatasetId).listItems();
for (const it of items) {
  const txt = it.markdown || it.text || "";
  const hasPrice = /\d+[,.]\d{2}\s*z[łl]/i.test(txt);
  console.log("url:", it.url, "| chars:", txt.length, "| hasPrice:", hasPrice);
  console.log("sample:", txt.slice(0, 400).replace(/\s+/g," "));
}
