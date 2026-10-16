// Checks worker/metar-proxy.js with a stand-in for NOAA (no network).
// Usage: node tests/check_worker.mjs
import assert from "node:assert/strict";
import worker, { parseIds } from "../worker/metar-proxy.js";

const calls = [];
globalThis.fetch = async (url) => {
  calls.push(String(url));
  const ids = new URL(url).searchParams.get("ids").split(",");
  if (ids.includes("WXXX")) return new Response("down", { status: 503 });
  return new Response(ids.map(id => `METAR ${id} 080230Z 05008KT 9999 FEW020 30/24 Q1009`).join("\n"));
};
const PAGE = "https://rrrrridh.github.io";
const get = (q, origin = PAGE, method = "GET") =>
  worker.fetch(new Request(`https://metar.example.workers.dev/${q}`, { method, headers: origin ? { Origin: origin } : {} }), {}, { waitUntil() {} });

let failed = 0;
const test = async (name, fn) => {
  try { await fn(); console.log(`ok   ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n     ${e.message}`); }
};

await test("station list is validated", () => {
  assert.deepEqual(parseIds("wiii, WADD,WIII"), ["WADD", "WIII"]);
  assert.equal(parseIds(""), null);
  assert.equal(parseIds("KJFK"), null);
  assert.equal(parseIds("WIII,../x"), null);
  assert.equal(parseIds(Array.from({ length: 201 }, (_, i) => "WA" + String.fromCharCode(65 + (i % 26)) + String.fromCharCode(65 + Math.floor(i / 26))).join(",")), null);
});

await test("returns raw METAR with CORS for the dashboard origin", async () => {
  calls.length = 0;
  const res = await get("?ids=WIII,WADD");
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), PAGE);
  assert.equal(res.headers.get("Access-Control-Expose-Headers"), "X-Fetched");
  assert.ok(Date.parse(res.headers.get("X-Fetched")) > 0);
  assert.match(await res.text(), /METAR WADD 080230Z[\s\S]*METAR WIII 080230Z/);
  assert.equal(calls.length, 1);
  assert.match(calls[0], /^https:\/\/aviationweather\.gov\/api\/data\/metar\?ids=WADD%2CWIII&format=raw&hours=3$/);
});

await test("long lists are split into batches of 40", async () => {
  calls.length = 0;
  const ids = Array.from({ length: 95 }, (_, i) => "WA" + String.fromCharCode(65 + (i % 26)) + String.fromCharCode(65 + Math.floor(i / 26)));
  const res = await get(`?ids=${ids.join(",")}`);
  assert.equal(res.status, 200);
  assert.equal(calls.length, 3);
  assert.equal((await res.text()).split("\n").length, 95);
});

await test("other sites are refused, preflight is answered", async () => {
  const other = await get("?ids=WIII", "https://evil.example");
  assert.equal(other.status, 403);
  assert.equal(other.headers.get("Access-Control-Allow-Origin"), null);
  const pre = await get("?ids=WIII", PAGE, "OPTIONS");
  assert.equal(pre.status, 204);
  assert.equal(pre.headers.get("Access-Control-Allow-Origin"), PAGE);
  assert.equal((await get("?ids=WIII", PAGE, "POST")).status, 405);
});

await test("bad input and NOAA errors give clear status codes", async () => {
  assert.equal((await get("?ids=KJFK")).status, 400);
  assert.equal((await get("")).status, 400);
  const down = await get("?ids=WXXX");
  assert.equal(down.status, 502);
  assert.equal(down.headers.get("Access-Control-Allow-Origin"), PAGE);
});

if (failed) { console.log(`\n${failed} check(s) failed`); process.exit(1); }
console.log("\nall worker checks passed");
