"use client";

import { useState, useRef, useEffect } from "react";

interface FunnelData {
  pageview: number;
  search_submitted: number;
  receipt_scanned: number;
  list_shared: number;
  install_clicked: number;
}

interface RecentEvent {
  event: string;
  created_at: string;
  properties: any;
  path: string | null;
  referrer: string | null;
}

interface EventsData {
  days: number;
  total_events: number;
  unique_sessions: number;
  unique_ips: number;
  counts: Record<string, number>;
  funnel: FunnelData;
  by_day: Record<string, number>;
  top_referrers: { host: string; count: number }[];
  recent: RecentEvent[];
}

function pct(part: number, whole: number): string {
  if (!whole) return "0%";
  return `${((part / whole) * 100).toFixed(1)}%`;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "teraz";
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

export default function EventsPage() {
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authError, setAuthError] = useState(false);
  const [data, setData] = useState<EventsData | null>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const token = useRef("");

  async function load(token0?: string) {
    setLoading(true);
    const res = await fetch(`/api/admin/events?days=${days}`, {
      headers: { Authorization: `Bearer ${token0 ?? token.current}` },
    });
    if (!res.ok) { setLoading(false); return; }
    setData(await res.json());
    setLoading(false);
  }

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(false);
    setLoading(true);
    const res = await fetch(`/api/admin/events?days=${days}`, {
      headers: { Authorization: `Bearer ${password}` },
    });
    if (!res.ok) {
      setAuthError(true);
      setLoading(false);
      return;
    }
    token.current = password;
    setData(await res.json());
    setAuthed(true);
    setLoading(false);
  }

  useEffect(() => {
    if (authed) load();
  }, [days]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!authed) {
    return (
      <main className="min-h-screen bg-[#f0f0eb] flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-sm p-8 w-full max-w-sm">
          <h1 className="text-2xl font-black text-gray-900 mb-1">Events</h1>
          <p className="text-gray-400 text-sm mb-6">Analityka użytkowników</p>
          <form onSubmit={login} className="space-y-3">
            <input
              type="password"
              placeholder="Hasło"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setAuthError(false); }}
              className={`w-full border rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-green-500 ${
                authError ? "border-red-300 bg-red-50" : "border-gray-200"
              }`}
            />
            {authError && <p className="text-red-500 text-xs">Nieprawidłowe hasło</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-500 hover:bg-green-600 disabled:opacity-60 text-white font-bold py-3 rounded-xl text-sm transition-all"
            >
              {loading ? "Ładowanie..." : "Zaloguj"}
            </button>
          </form>
        </div>
      </main>
    );
  }

  if (!data) {
    return <main className="min-h-screen bg-[#f0f0eb] p-4">Ładowanie...</main>;
  }

  const f = data.funnel;
  const dayEntries = Object.entries(data.by_day).sort(([a], [b]) => a.localeCompare(b));
  const maxDay = Math.max(...dayEntries.map(([, v]) => v), 1);

  return (
    <main className="min-h-screen bg-[#f0f0eb] p-4">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-black text-gray-900">Analityka</h1>
            <p className="text-gray-400 text-sm">Ostatnie {data.days} dni</p>
          </div>
          <div className="flex gap-2">
            {[1, 7, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-2 text-sm font-semibold rounded-xl ${
                  days === d ? "bg-green-500 text-white" : "bg-white text-gray-500"
                }`}
              >
                {d === 1 ? "Dziś" : `${d}d`}
              </button>
            ))}
            <button
              onClick={() => load()}
              disabled={loading}
              className="bg-gray-900 hover:bg-gray-800 text-white text-sm font-bold px-3 py-2 rounded-xl"
            >
              {loading ? "..." : "Odśwież"}
            </button>
          </div>
        </div>

        {/* Top numbers */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Sesje</p>
            <p className="text-3xl font-black text-gray-900 leading-none mt-1">{data.unique_sessions}</p>
            <p className="text-xs text-gray-400 mt-1">unikalnych użytkowników</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Eventy</p>
            <p className="text-3xl font-black text-gray-900 leading-none mt-1">{data.total_events}</p>
            <p className="text-xs text-gray-400 mt-1">w wybranym okresie</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">IP</p>
            <p className="text-3xl font-black text-gray-900 leading-none mt-1">{data.unique_ips}</p>
            <p className="text-xs text-gray-400 mt-1">unikalnych adresów</p>
          </div>
        </div>

        {/* Funnel */}
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Lejek konwersji (unikalne sesje)</p>
          <div className="space-y-3">
            {[
              { label: "Wizyta",            count: f.pageview,        color: "bg-blue-500" },
              { label: "Wyszukiwanie",      count: f.search_submitted, color: "bg-green-500" },
              { label: "Skan paragonu",     count: f.receipt_scanned,  color: "bg-orange-500" },
              { label: "Udostępnienie",     count: f.list_shared,      color: "bg-purple-500" },
              { label: "Install PWA",       count: f.install_clicked,  color: "bg-pink-500" },
            ].map((step, i, arr) => {
              const widthPct = f.pageview > 0 ? (step.count / f.pageview) * 100 : 0;
              const fromPrev = i === 0 ? null : pct(step.count, arr[i - 1].count);
              return (
                <div key={step.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-gray-700">{step.label}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-400">{pct(step.count, f.pageview)} z wizyt</span>
                      {fromPrev && <span className="text-xs text-gray-400">{fromPrev} z poprzedniego</span>}
                      <span className="text-lg font-black text-gray-900">{step.count}</span>
                    </div>
                  </div>
                  <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div className={`h-full ${step.color}`} style={{ width: `${Math.max(2, widthPct)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* By day */}
        {dayEntries.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-5">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Wizyty dziennie</p>
            <div className="space-y-2">
              {dayEntries.map(([day, count]) => (
                <div key={day} className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-500 w-24 shrink-0">{day.slice(5)}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${(count / maxDay) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold text-gray-700 w-10 text-right">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Counts by event */}
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Wszystkie eventy</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.counts)
              .sort(([, a], [, b]) => b - a)
              .map(([event, count]) => (
                <div key={event} className="flex items-center justify-between border border-gray-100 rounded-xl px-3 py-2">
                  <span className="text-sm font-mono text-gray-600">{event}</span>
                  <span className="text-lg font-black text-gray-900">{count}</span>
                </div>
              ))}
          </div>
        </div>

        {/* Top referrers */}
        {data.top_referrers.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-5">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Skąd przychodzą</p>
            <ul className="divide-y divide-gray-50">
              {data.top_referrers.map((r) => (
                <li key={r.host} className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-700 truncate">{r.host}</span>
                  <span className="font-bold text-gray-900">{r.count}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recent events */}
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Ostatnie eventy</p>
          <ul className="divide-y divide-gray-50 text-xs">
            {data.recent.map((e, i) => (
              <li key={i} className="py-2 flex items-start gap-3">
                <span className="text-gray-300 w-12 shrink-0 mt-0.5">{timeAgo(e.created_at)}</span>
                <span className="font-mono font-bold text-gray-700 w-40 shrink-0 truncate">{e.event}</span>
                <span className="text-gray-400 truncate flex-1">
                  {e.properties ? JSON.stringify(e.properties) : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </main>
  );
}
