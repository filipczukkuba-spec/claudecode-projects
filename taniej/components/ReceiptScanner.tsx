"use client";

import { useState, useRef } from "react";
import { track } from "@vercel/analytics";

interface AcceptedItem { product: string; price: number; unit_type: string | null; is_promo: boolean }
interface RejectedItem { raw: string; reason: string }
interface ScanResult {
  ok: true;
  store: string;
  receipt_date: string;
  total: number | null;
  accepted: AcceptedItem[];
  rejected: RejectedItem[];
  saved: number;
}

function fmt(n: number) {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function rejectReasonLabel(r: string) {
  switch (r) {
    case "no_match":    return "nie rozpoznano produktu";
    case "outlier":     return "cena podejrzanie wysoka";
    case "invalid_price": return "nieprawidłowa cena";
    default:            return r;
  }
}

export default function ReceiptScanner() {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [city, setCity] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function pick(file: File | null) {
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      setError("Zdjęcie zbyt duże (max 8 MB)");
      return;
    }
    setError(null);
    setResult(null);
    setFile(file);
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(file);
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setSending(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function submit() {
    if (!file) return;
    setSending(true);
    setError(null);
    setResult(null);
    try {
      const form = new FormData();
      form.append("receipt", file);
      if (city.trim()) form.append("city", city.trim());
      const res = await fetch("/api/scan-receipt", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) {
        track("receipt_scan_failed", { reason: (data.error ?? "unknown").slice(0, 60) });
        setError(data.error ?? "Coś poszło nie tak");
        return;
      }
      track("receipt_scanned", {
        store: (data as ScanResult).store,
        saved: (data as ScanResult).saved,
        rejected: (data as ScanResult).rejected.length,
      });
      setResult(data as ScanResult);
    } catch {
      setError("Błąd połączenia");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm mb-4 overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-5 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center text-white text-base shadow-sm">
            📸
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800">Zeskanuj paragon</p>
            <p className="text-xs text-gray-400 mt-0.5">Pomóż innym — dodaj prawdziwe ceny z półki</p>
          </div>
        </div>
        <span className="text-gray-300 text-sm ml-3">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-gray-50 space-y-4 pt-4">
          {!preview && !result && (
            <>
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-3">
                <p className="text-xs text-amber-700 leading-relaxed">
                  <span className="font-bold">Ważne:</span> paragon musi być <span className="font-bold">z ostatnich 7 dni</span>.
                  Wyraźne zdjęcie z widoczną nazwą sklepu, datą i sumą (SUMA PLN).
                  Twoje dane pomogą innym znaleźć tańsze zakupy 🙏
                </p>
              </div>

              <label className="block">
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={(e) => pick(e.target.files?.[0] ?? null)}
                />
                <div className="border-2 border-dashed border-gray-200 hover:border-green-400 rounded-2xl py-8 text-center cursor-pointer transition-colors">
                  <p className="text-4xl mb-2">📷</p>
                  <p className="text-sm font-bold text-gray-700">Zrób zdjęcie paragonu</p>
                  <p className="text-xs text-gray-400 mt-1">albo wybierz z galerii</p>
                </div>
              </label>
            </>
          )}

          {preview && !result && (
            <>
              <div className="relative rounded-2xl overflow-hidden bg-gray-100">
                <img src={preview} alt="paragon" className="w-full max-h-72 object-contain bg-black" />
                <button
                  onClick={reset}
                  className="absolute top-2 right-2 bg-black/70 hover:bg-black/90 text-white w-8 h-8 rounded-full flex items-center justify-center text-sm"
                  title="Inne zdjęcie"
                >
                  ×
                </button>
              </div>

              <input
                type="text"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-700 outline-none focus:border-green-400 transition-colors"
                placeholder="Miasto (opcjonalnie)"
                value={city}
                onChange={(e) => setCity(e.target.value)}
              />

              {error && (
                <div className="bg-red-50 border border-red-100 rounded-xl px-3 py-2 text-xs text-red-600 font-medium">
                  {error}
                </div>
              )}

              <button
                onClick={submit}
                disabled={sending}
                className="w-full bg-green-500 hover:bg-green-600 active:scale-[0.98] disabled:opacity-60 transition-all text-white font-black text-base rounded-2xl py-4"
              >
                {sending ? "Czytam paragon..." : "Wyślij paragon"}
              </button>
              <p className="text-center text-xs text-gray-400">
                Sprawdzimy datę, sumę i dopasujemy produkty. To może chwilę zająć.
              </p>
            </>
          )}

          {result && (
            <div className="space-y-3">
              <div className="bg-green-50 border border-green-100 rounded-2xl p-4 text-center">
                <p className="text-3xl mb-1">✅</p>
                <p className="font-black text-green-700 text-base">Dziękujemy!</p>
                <p className="text-xs text-green-600 mt-1">
                  Dodaliśmy <span className="font-bold">{result.saved}</span> {result.saved === 1 ? "cenę" : "cen"} z {result.store}
                </p>
                <p className="text-[10px] text-green-500 mt-0.5">
                  Paragon z {result.receipt_date}{result.total ? ` · suma ${fmt(result.total)} zł` : ""}
                </p>
              </div>

              {result.accepted.length > 0 && (
                <div className="bg-white border border-gray-100 rounded-xl">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest px-4 pt-3 pb-2">
                    Zapisane ceny
                  </p>
                  <ul className="divide-y divide-gray-50">
                    {result.accepted.map((a, i) => {
                      const unitLabel =
                        a.unit_type === "kg" ? "/kg" :
                        a.unit_type === "l"  ? "/l"  :
                        a.unit_type === "szt" ? "/szt" : "";
                      return (
                        <li key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                          <span className="text-gray-700 truncate">{a.product}</span>
                          <div className="flex items-center gap-2 shrink-0">
                            {a.is_promo && (
                              <span className="text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                                PROMO
                              </span>
                            )}
                            <span className="font-bold text-gray-900">
                              {fmt(a.price)} zł
                              {unitLabel && <span className="text-xs text-gray-400 font-normal">{unitLabel}</span>}
                            </span>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {result.rejected.length > 0 && (
                <details className="bg-gray-50 rounded-xl">
                  <summary className="px-4 py-2.5 text-xs text-gray-500 cursor-pointer font-medium">
                    Pominięto {result.rejected.length} {result.rejected.length === 1 ? "pozycję" : "pozycji"}
                  </summary>
                  <ul className="px-4 pb-3 text-xs text-gray-400 space-y-1">
                    {result.rejected.map((r, i) => (
                      <li key={i}>{r.raw} — {rejectReasonLabel(r.reason)}</li>
                    ))}
                  </ul>
                </details>
              )}

              <button
                onClick={reset}
                className="w-full bg-gray-900 hover:bg-gray-800 active:scale-[0.98] transition-all text-white font-bold text-sm rounded-xl py-3"
              >
                Zeskanuj kolejny paragon
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
