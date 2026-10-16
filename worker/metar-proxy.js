// Cloudflare Worker: lets the dashboard fetch live METAR from NOAA AWC in the browser.
//
// NOAA's API sends no CORS headers, so a page on GitHub Pages cannot call it directly.
// This worker forwards one request (GET /?ids=WIII,WADD,...) to NOAA and returns the raw
// METAR text with CORS headers for the dashboard's own origin. It only accepts Indonesian
// ICAO codes (W...), and caches each answer for two minutes so repeated clicks do not
// reach NOAA. It holds no secrets.
//
// Deploy: see docs/metar-live.md.

const AWC_URL = "https://aviationweather.gov/api/data/metar";
const ALLOWED_ORIGINS = [
  "https://rrrrridh.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];
const MAX_IDS = 200;
const BATCH = 40;          // stations per NOAA request
const CACHE_SECONDS = 120;

function corsHeaders(origin) {
  const h = { "Vary": "Origin" };
  if (ALLOWED_ORIGINS.includes(origin)) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Methods"] = "GET, OPTIONS";
    h["Access-Control-Max-Age"] = "86400";
    h["Access-Control-Expose-Headers"] = "X-Fetched";
  }
  return h;
}

function reply(status, body, origin, extra = {}) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8", ...corsHeaders(origin), ...extra },
  });
}

export function parseIds(param) {
  const ids = [...new Set(String(param || "").toUpperCase().split(",").map(s => s.trim()).filter(Boolean))];
  if (!ids.length || ids.length > MAX_IDS || !ids.every(id => /^W[A-Z]{3}$/.test(id))) return null;
  return ids.sort();
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") return reply(204, null, origin);
    if (request.method !== "GET") return reply(405, "Only GET is supported.", origin);
    if (origin && !ALLOWED_ORIGINS.includes(origin)) return reply(403, "Origin not allowed.", origin);

    const url = new URL(request.url);
    const ids = parseIds(url.searchParams.get("ids"));
    if (!ids) return reply(400, `Pass ids=ICAO,ICAO,... (1-${MAX_IDS} Indonesian codes, W...).`, origin);

    // One cache entry per station list, shared by every visitor.
    const cache = typeof caches !== "undefined" ? caches.default : null;
    const key = new Request(`${url.origin}/?ids=${ids.join(",")}`);
    let cached = cache && await cache.match(key);
    if (!cached) {
      const parts = [];
      for (let i = 0; i < ids.length; i += BATCH) {
        const q = new URLSearchParams({ ids: ids.slice(i, i + BATCH).join(","), format: "raw", hours: "3" });
        const res = await fetch(`${AWC_URL}?${q}`, { headers: { "User-Agent": "JamBandaraIndonesia/1.0 (+https://github.com/rrrrridh/Indonesia-airport-lt)" } });
        if (!res.ok) return reply(502, `NOAA AWC answered HTTP ${res.status}.`, origin);
        parts.push(await res.text());
      }
      cached = new Response(parts.join("\n"), {
        headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": `public, max-age=${CACHE_SECONDS}`, "X-Fetched": new Date().toISOString() },
      });
      if (cache) ctx.waitUntil(cache.put(key, cached.clone()));
    }
    return reply(200, await cached.text(), origin, {
      "Cache-Control": `public, max-age=${CACHE_SECONDS}`,
      "X-Fetched": cached.headers.get("X-Fetched") || new Date().toISOString(),
    });
  },
};
