// Checks the built page: every inline script parses, and the page's pure helpers
// (time zones, sunrise/sunset, METAR decoding, distance) give known answers.
// Usage: node tests/check_page.mjs index.html
import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const file = process.argv[2] || "index.html";
const html = fs.readFileSync(file, "utf8");
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.ok(scripts.length > 0, "no inline <script> found");
scripts.forEach((code, i) => new vm.Script(code, { filename: `${file}#script${i}` }));  // throws on syntax errors

// The part of the main script before the 3D scene uses no DOM or WebGL, so it can run here.
const main = scripts.find(s => s.includes("const AIRPORTS"));
const cut = main.indexOf("/* =====================  3D SCENE");
assert.ok(cut > 0, "3D SCENE marker not found");
const api = vm.runInNewContext(main.slice(0, cut) + `
;({ AIRPORTS, ZONES, zoneNow, sunTimes, decodeMetar, wxText, distanceKm, bearingDeg, compassName, flightMinutes, offsetText })`);

let failed = 0;
const test = (name, fn) => {
  try { fn(); console.log(`ok   ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n     ${e.message}`); }
};
const hm = (ms, offset) => { const d = new Date(ms + offset * 3600e3); return d.getUTCHours() * 60 + d.getUTCMinutes(); };
const near = (actual, expected, tol, label) => assert.ok(Math.abs(actual - expected) <= tol, `${label}: ${actual} not within ${tol} of ${expected}`);
const byIata = code => api.AIRPORTS.find(a => a.iata === code);

test("airport list is injected and well formed", () => {
  assert.ok(api.AIRPORTS.length >= 100, `only ${api.AIRPORTS.length} airports`);
  for (const a of api.AIRPORTS) {
    assert.match(a.icao, /^W[A-Z]{3}$/, a.iata);
    assert.ok(api.ZONES[a.zone], `${a.iata} has unknown zone ${a.zone}`);
  }
});

test("zone clocks use fixed offsets", () => {
  const t = Date.UTC(2026, 9, 8, 3, 5, 9);
  assert.equal(api.zoneNow("WIB", t).hm, "10:05");
  assert.equal(api.zoneNow("WITA", t).hm, "11:05");
  assert.equal(api.zoneNow("WIT", t).hm, "12:05");
});

test("sunrise/sunset for Jakarta on 7 Oct 2026 (≈05:36 / 17:48 WIB)", () => {
  const s = api.sunTimes(-6.1256, 106.6559, Date.UTC(2026, 9, 7, 5));
  near(hm(s.rise, 7), 5 * 60 + 36, 2, "sunrise");
  near(hm(s.set, 7), 17 * 60 + 48, 2, "sunset");
});

test("METAR decoding and flight category", () => {
  const vfr = api.decodeMetar("METAR WIII 080230Z 05008KT 9000 FEW018CB SCT020 31/24 Q1009 NOSIG=");
  assert.equal(vfr.cat, "VFR");
  assert.equal(vfr.temp, 31); assert.equal(vfr.qnh, 1009); assert.equal(vfr.trend, "NOSIG");
  const ifr = api.decodeMetar("SPECI WADD 080245Z 10012G22KT 3000 +TSRA BKN008CB 27/25 Q1010 TEMPO 2000 +TSRA=");
  assert.equal(ifr.cat, "IFR"); assert.equal(ifr.wind.gust, 22); assert.ok(ifr.thunder && ifr.rain);
  assert.equal(api.decodeMetar("METAR WIOO 080200Z 00000KT 0800 FG VV002 24/24 Q1011=").cat, "LIFR");
  assert.equal(api.decodeMetar("METAR WAJJ 080200Z VRB02KT CAVOK 28/23 Q1011=").vis, 10000);
  assert.equal(api.wxText("VCSH"), "Hujan lokal (shower) di sekitar bandara");
});

test("distance, bearing and flight estimate between airports", () => {
  const cgk = byIata("CGK"), dps = byIata("DPS"), djj = byIata("DJJ");
  near(api.distanceKm(cgk, dps), 980, 25, "CGK–DPS km");
  near(api.distanceKm(cgk, djj), 3770, 60, "CGK–DJJ km");
  near(api.bearingDeg(cgk, dps), 108, 2, "CGK→DPS bearing (east-southeast)");
  assert.equal(api.compassName(90), "Timur");
  assert.equal(api.compassName(350), "Utara");
  assert.equal(api.flightMinutes(780), 90);
  assert.equal(api.offsetText(cgk, djj), "DJJ 2 jam lebih cepat dari CGK");
  assert.equal(api.offsetText(djj, cgk), "CGK 2 jam lebih lambat dari DJJ");
});

if (failed) { console.log(`\n${failed} check(s) failed`); process.exit(1); }
console.log("\nall page checks passed");
