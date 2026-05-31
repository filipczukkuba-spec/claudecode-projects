import { ApifyClient } from "apify-client";
import { readFileSync } from "fs";
const env = readFileSync(".env.local","utf8");
const token = env.match(/APIFY_TOKEN=(.+)/)[1].trim();
const client = new ApifyClient({ token });
try{
  const me = await client.user("me").get();
  console.log("USER OK:", me.username);
}catch(e){console.log("TOKEN ERR:", e.message)}
