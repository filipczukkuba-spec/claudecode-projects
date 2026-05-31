// Generates the source images @capacitor/assets needs, from the brand art in
// public/icon.svg. Produces assets/{icon,icon-foreground,icon-background,
// splash,splash-dark}.png. Then run:
//   npx @capacitor/assets generate --android --ios
//   npx cap sync
// Run: node scripts/gen-mobile-assets.mjs
import sharp from "sharp";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "assets");
const GREEN = { r: 22, g: 163, b: 74, alpha: 1 }; // #16a34a
const iconSvgPath = join(root, "public", "icon.svg");

await mkdir(out, { recursive: true });

// Full rounded brand icon → legacy Android launcher + iOS app icon.
await sharp(iconSvgPath, { density: 384 })
  .resize(1024, 1024, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toFile(join(out, "icon.png"));

// Adaptive icon background: solid brand green.
await sharp({ create: { width: 1024, height: 1024, channels: 4, background: GREEN } })
  .png()
  .toFile(join(out, "icon-background.png"));

// Adaptive icon foreground: cart + arrow only (no background rect) on a
// transparent canvas, scaled into the ~66% adaptive safe zone so the launcher
// mask never clips the art.
const FG_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <g fill="none" stroke="#ffffff" stroke-width="28" stroke-linecap="round" stroke-linejoin="round">
    <path d="M120 132 h44 l40 196 h160 l36 -136 H196" />
    <circle cx="220" cy="392" r="20" fill="#ffffff" stroke="none"/>
    <circle cx="384" cy="392" r="20" fill="#ffffff" stroke="none"/>
  </g>
  <g fill="#facc15">
    <path d="M360 120 l64 0 0 64 -22 -22 -52 52 -20 -20 52 -52 z"/>
  </g>
</svg>`;
const artSize = Math.round(1024 * 0.6); // safe-zone scale
const art = await sharp(Buffer.from(FG_SVG), { density: 512 })
  .resize(artSize, artSize, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toBuffer();
await sharp({ create: { width: 1024, height: 1024, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
  .composite([{ input: art, gravity: "center" }])
  .png()
  .toFile(join(out, "icon-foreground.png"));

// Splash: brand-green 2732² canvas with the logo centered (~36% width).
const logo = await sharp(iconSvgPath, { density: 384 }).resize(980, 980).png().toBuffer();
const splash = await sharp({ create: { width: 2732, height: 2732, channels: 4, background: GREEN } })
  .composite([{ input: logo, gravity: "center" }])
  .png()
  .toBuffer();
await sharp(splash).toFile(join(out, "splash.png"));
await sharp(splash).toFile(join(out, "splash-dark.png"));

console.log("Wrote source assets to assets/");
