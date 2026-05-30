import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "taniejkupuj — porównywarka cen w polskich sklepach";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: "linear-gradient(135deg, #22c55e 0%, #059669 50%, #047857 100%)",
          padding: 80,
          position: "relative",
          fontFamily: "sans-serif",
        }}
      >
        {/* Decorative circles */}
        <div
          style={{
            position: "absolute",
            top: -100,
            right: -100,
            width: 400,
            height: 400,
            borderRadius: 9999,
            background: "rgba(255,255,255,0.08)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -80,
            left: -60,
            width: 300,
            height: 300,
            borderRadius: 9999,
            background: "rgba(255,255,255,0.08)",
          }}
        />

        {/* Main content */}
        <div style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 32 }}>
          <div
            style={{
              fontSize: 90,
              fontWeight: 900,
              color: "white",
              letterSpacing: -3,
              lineHeight: 1,
              display: "flex",
            }}
          >
            taniejkupuj
          </div>
          <div style={{ fontSize: 72, display: "flex" }}>🛒</div>
        </div>

        <div
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: "white",
            lineHeight: 1.15,
            marginBottom: 40,
            maxWidth: 980,
            display: "flex",
          }}
        >
          Porównaj ceny w 7 sklepach jednocześnie
        </div>

        {/* Store pills */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 40 }}>
          {["Biedronka", "Lidl", "Kaufland", "Aldi", "Netto", "Auchan", "Carrefour"].map((s) => (
            <div
              key={s}
              style={{
                background: "rgba(255,255,255,0.22)",
                color: "white",
                fontSize: 26,
                fontWeight: 700,
                padding: "10px 22px",
                borderRadius: 999,
                display: "flex",
              }}
            >
              {s}
            </div>
          ))}
        </div>

        {/* Bottom stat bar */}
        <div style={{ marginTop: "auto", display: "flex", gap: 48, alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ color: "white", fontSize: 64, fontWeight: 900, lineHeight: 1 }}>500+</div>
            <div style={{ color: "rgba(255,255,255,0.85)", fontSize: 22, marginTop: 6 }}>produktów</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ color: "white", fontSize: 64, fontWeight: 900, lineHeight: 1 }}>codziennie</div>
            <div style={{ color: "rgba(255,255,255,0.85)", fontSize: 22, marginTop: 6 }}>aktualizowane</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ color: "white", fontSize: 64, fontWeight: 900, lineHeight: 1 }}>gratis</div>
            <div style={{ color: "rgba(255,255,255,0.85)", fontSize: 22, marginTop: 6 }}>bez logowania</div>
          </div>
        </div>

        {/* URL */}
        <div
          style={{
            position: "absolute",
            bottom: 50,
            right: 80,
            color: "rgba(255,255,255,0.9)",
            fontSize: 28,
            fontWeight: 700,
            display: "flex",
          }}
        >
          taniejkupuj.pl
        </div>
      </div>
    ),
    { ...size }
  );
}
