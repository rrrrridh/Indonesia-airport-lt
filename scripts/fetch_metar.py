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
import http.cookiejar
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
# BMKG's portal answers 403 to anything that does not look like a browser, so send browser-like headers.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
}
UA = "JamBandaraNusantara/1.0 (+https://github.com/rrrrridh/Indonesia-airport-lt)"
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


class Browser:
    """Tiny cookie-keeping client that returns the response even for HTTP errors, so they can be logged."""

    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, url, data=None, headers=None, timeout=40):
        h = dict(BROWSER_HEADERS)
        h.update(headers or {})
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            with self.opener.open(req, timeout=timeout) as r:
                return r.status, r.headers, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8", "replace")
        except Exception as e:  # DNS, TLS, timeout...
            return 0, {}, f"{type(e).__name__}: {e}"


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


def describe(status, headers, body):
    keep = {k.lower(): v for k, v in dict(headers).items()}
    hints = {k: keep[k] for k in ("server", "via", "cf-ray", "x-cache", "x-served-by", "content-type") if k in keep}
    snippet = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:160]
    return f"HTTP {status} {hints} body: {snippet!r}"


def parse_form(page):
    """Find the METAR query form: (action, method, {name: default}, text_field_names)."""
    m = re.search(r"<form\b([^>]*)>(.*?)</form>", page, re.S | re.I)
    if not m:
        return None
    attrs, inner = m.groups()
    attr = lambda n: (re.search(n + r"\s*=\s*[\"']([^\"']*)[\"']", attrs, re.I) or [None, None])[1]
    fields, texts = {}, []
    for tag in re.findall(r"<(?:input|textarea|select)\b[^>]*>", inner, re.I):
        name = re.search(r"name\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
        if not name:
            continue
        kind = (re.search(r"type\s*=\s*[\"']([^\"']+)[\"']", tag, re.I) or [None, "text"])[1].lower()
        value = (re.search(r"value\s*=\s*[\"']([^\"']*)[\"']", tag, re.I) or [None, ""])[1]
        fields[name.group(1)] = value
        if kind in ("text", "search") or tag.lower().startswith("<textarea"):
            texts.append(name.group(1))
    return attr("action") or "", (attr("method") or "get").upper(), fields, texts


def from_bmkg(icaos, now):
    wanted = set(icaos)
    query = " ".join(icaos)
    forced = os.environ.get("BMKG_METAR_FIELD")
    browser = Browser()

    status, headers, page = browser.request(BMKG_URL)
    print(f"BMKG GET {BMKG_URL}: {describe(status, headers, page)}", file=sys.stderr)
    found = parse_reports(page, wanted, now) if status == 200 else {}
    if found:
        return found

    form = parse_form(page) if status == 200 else None
    if form:
        action, method, defaults, texts = form
        print(f"BMKG form: method={method} action={action!r} fields={defaults} text_fields={texts}", file=sys.stderr)
    # Build submissions: the discovered form first, then common field names.
    attempts = []
    target_default = urllib.parse.urljoin(BMKG_URL, form[0]) if form and form[0] else BMKG_URL
    names = [forced] if forced else (form[3] if form and form[3] else []) + ["icao", "kode", "code", "station", "icao_code"]
    method = (os.environ.get("BMKG_METAR_METHOD") or (form[1] if form else "POST")).upper()
    for field in dict.fromkeys(names):
        payload = dict(form[2]) if form else {}
        payload[field] = query
        attempts.append((method, field, payload))

    for method, field, payload in attempts:
        enc = urllib.parse.urlencode(payload)
        hdr = {"Referer": BMKG_URL, "Origin": BMKG_URL.split("/web/")[0]}
        if method == "GET":
            status, headers, text = browser.request(target_default + ("&" if "?" in target_default else "?") + enc, headers=hdr)
        else:
            hdr["Content-Type"] = "application/x-www-form-urlencoded"
            status, headers, text = browser.request(target_default, enc.encode(), hdr)
        found = parse_reports(text, wanted, now) if status == 200 else {}
        print(f"BMKG {method} {field}: {describe(status, headers, text)} -> {len(found)} stations", file=sys.stderr)
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
