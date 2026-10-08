"""Fetch the latest METAR/SPECI for every airport on the dashboard.

Primary source is BMKG's aviation portal; any station BMKG does not return is
filled from the NOAA Aviation Weather Center API, which redistributes the same
BMKG-issued reports. Output is a small JSON file the dashboard polls.

Usage:
  python3 scripts/fetch_metar.py data/metar.json

Environment overrides (BMKG has no documented API, so the request can be tuned
without code changes):
  BMKG_METAR_URL    page that answers a METAR query (default: web-aviation.bmkg.go.id/web/metar_speci.php)
  BMKG_METAR_FIELD  form field that carries the ICAO list; when unset several common names are tried
  BMKG_METAR_METHOD POST (default) or GET
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; JamBandaraNusantara/1.0; +https://github.com/rrrrridh/indonesia-airport-lt)"
BMKG_URL = os.environ.get("BMKG_METAR_URL") or "https://web-aviation.bmkg.go.id/web/metar_speci.php"
AWC_URL = "https://aviationweather.gov/api/data/metar"

REPORT_RE = re.compile(
    r"\b(?:(METAR|SPECI)\s+)?(?:COR\s+)?(W[A-Z]{3})\s+(\d{2})(\d{2})(\d{2})Z\b([^=\n<]*)",
)


def airport_icaos():
    src = (ROOT / "src" / "dashboard.html").read_text(encoding="utf-8")
    return re.findall(r'\[\s*"[A-Z]{3}",\s*"([A-Z]{4})"', src)


def http(url, data=None, timeout=40):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def obs_time(day, hh, mm, now):
    """METAR carries only day-of-month; pick the matching date at or just before now."""
    for month_ref in (now, (now.replace(day=1) - dt.timedelta(days=1))):
        try:
            t = month_ref.replace(day=day, hour=hh, minute=mm, second=0, microsecond=0)
        except ValueError:
            continue
        if t <= now + dt.timedelta(hours=1):
            return t
    return None


def parse_reports(text, wanted, now):
    """Return {icao: {raw, obs}} keeping the newest report per station."""
    text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    out = {}
    for m in REPORT_RE.finditer(text):
        kind, icao, day, hh, mm, body = m.groups()
        if icao not in wanted:
            continue
        t = obs_time(int(day), int(hh), int(mm), now)
        if t is None or now - t > dt.timedelta(hours=6):
            continue
        raw = " ".join(f"{kind or 'METAR'} {icao} {day}{hh}{mm}Z {body}".split()).rstrip(" =") + "="
        if icao not in out or t > out[icao]["_t"]:
            out[icao] = {"raw": raw, "obs": t.strftime("%Y-%m-%dT%H:%M:00Z"), "_t": t}
    return out


def from_bmkg(icaos, now):
    fields = [os.environ["BMKG_METAR_FIELD"]] if os.environ.get("BMKG_METAR_FIELD") else ["icao", "kode", "code", "station", "icao_code"]
    method = (os.environ.get("BMKG_METAR_METHOD") or "POST").upper()
    query = " ".join(icaos)
    for field in fields:
        try:
            if method == "GET":
                text = http(BMKG_URL + ("&" if "?" in BMKG_URL else "?") + urllib.parse.urlencode({field: query}))
            else:
                text = http(BMKG_URL, urllib.parse.urlencode({field: query}).encode())
        except Exception as e:  # network or HTTP error: try the next variant
            print(f"BMKG ({method} {field}): {e}", file=sys.stderr)
            continue
        found = parse_reports(text, set(icaos), now)
        print(f"BMKG ({method} {field}): {len(found)} stations", file=sys.stderr)
        if found:
            return found
    return {}


def from_awc(icaos, now):
    url = AWC_URL + "?" + urllib.parse.urlencode({"ids": ",".join(icaos), "format": "raw", "hours": 3})
    try:
        found = parse_reports(http(url), set(icaos), now)
    except Exception as e:
        print(f"AWC: {e}", file=sys.stderr)
        return {}
    print(f"AWC: {len(found)} stations", file=sys.stderr)
    return found


def main(out_path):
    now = dt.datetime.now(dt.timezone.utc)
    icaos = airport_icaos()
    stations = {}
    for k, v in from_bmkg(icaos, now).items():
        stations[k] = {**v, "source": "BMKG"}
    missing = [i for i in icaos if i not in stations]
    if missing:
        for k, v in from_awc(missing, now).items():
            stations[k] = {**v, "source": "NOAA AWC"}
    for v in stations.values():
        v.pop("_t", None)
    doc = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stations": dict(sorted(stations.items())),
        "missing": [i for i in icaos if i not in stations],
    }
    path = pathlib.Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(stations)}/{len(icaos)} stations written to {path}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/metar.json")
