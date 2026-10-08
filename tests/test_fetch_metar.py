"""Unit tests for scripts/fetch_metar.py (no network: HTTP calls are replaced)."""
import contextlib
import datetime as dt
import io
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import fetch_metar as fm  # noqa: E402

NOW = dt.datetime(2026, 10, 8, 3, 0, tzinfo=dt.timezone.utc)


def quiet():
    return contextlib.redirect_stderr(io.StringIO())


class ParseReports(unittest.TestCase):
    def test_keeps_newest_report_per_station_and_strips_html(self):
        text = (
            "<td>METAR WIII 080200Z 05008KT 9000 FEW018 31/24 Q1009 NOSIG=</td>"
            "<td>METAR WIII 080230Z 06010KT 9000 SCT020 31/24 Q1009 NOSIG=</td>"
            "<td>SPECI WADD 080245Z 10012G22KT 3000 +TSRA BKN008CB 27/25 Q1010=</td>"
        )
        got = fm.parse_reports(text, {"WIII", "WADD"}, NOW)
        self.assertEqual(set(got), {"WIII", "WADD"})
        self.assertIn("080230Z", got["WIII"]["raw"])
        self.assertTrue(got["WADD"]["raw"].startswith("SPECI WADD"))
        self.assertEqual(got["WIII"]["obs"], "2026-10-08T02:30:00Z")

    def test_ignores_old_and_unwanted_reports(self):
        text = "METAR WIII 072000Z 00000KT 9999 FEW020 28/24 Q1010=\nMETAR WAAA 080230Z 00000KT 9999 FEW020 28/24 Q1010="
        self.assertEqual(fm.parse_reports(text, {"WIII"}, NOW), {})  # 7 hours old; WAAA not wanted

    def test_previous_month_day(self):
        now = dt.datetime(2026, 10, 1, 1, 0, tzinfo=dt.timezone.utc)
        got = fm.parse_reports("METAR WIII 302330Z 00000KT 9999 FEW020 28/24 Q1010=", {"WIII"}, now)
        self.assertEqual(got["WIII"]["obs"], "2026-09-30T23:30:00Z")


class BmkgHelpers(unittest.TestCase):
    def test_detects_cloudflare_challenge(self):
        self.assertTrue(fm.is_bot_challenge(403, {"Server": "cloudflare"}, "<title>Just a moment...</title>"))
        self.assertTrue(fm.is_bot_challenge(503, {}, "<title>Just a moment...</title>"))
        self.assertFalse(fm.is_bot_challenge(200, {"Server": "cloudflare"}, "ok"))
        self.assertFalse(fm.is_bot_challenge(404, {"Server": "nginx"}, "not found"))

    def test_parse_form_finds_action_fields_and_text_inputs(self):
        page = ('<form method="post" action="metar_speci.php"><input type="hidden" name="tok" value="t1">'
                '<input type="text" name="lokasi"><input type="submit" value="Cari"></form>')
        action, method, fields, texts = fm.parse_form(page)
        self.assertEqual((action, method), ("metar_speci.php", "POST"))
        self.assertEqual(fields["tok"], "t1")
        self.assertEqual(texts, ["lokasi"])

    def test_challenge_stops_after_one_request(self):
        calls = []

        def fake_request(self, url, data=None, headers=None, timeout=40):
            calls.append(url)
            return 403, {"Server": "cloudflare"}, "<title>Just a moment...</title>"

        with mock.patch.object(fm.Browser, "request", fake_request), quiet():
            self.assertEqual(fm.from_bmkg(["WIII"], NOW), {})
        self.assertEqual(len(calls), 1)


class Awc(unittest.TestCase):
    def test_batches_ids_and_merges_results(self):
        icaos = [f"WA{chr(65 + i // 26)}{chr(65 + i % 26)}" for i in range(95)]
        sizes = []

        def fake_get_text(url, data=None, timeout=40):
            ids = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["ids"][0].split(",")
            sizes.append(len(ids))
            return "\n".join(f"{i} 080230Z 00000KT 9999 FEW020 30/24 Q1009" for i in ids[:2])

        with mock.patch.object(fm, "get_text", fake_get_text), quiet():
            got = fm.from_awc(icaos, NOW, batch=40)
        self.assertEqual(sizes, [40, 40, 15])
        self.assertEqual(len(got), 6)


class Main(unittest.TestCase):
    def test_bmkg_crash_falls_back_to_noaa(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "metar.json"
            with mock.patch.object(fm, "airport_icaos", return_value=["WIII", "WADD"]), \
                 mock.patch.object(fm, "from_bmkg", side_effect=RuntimeError("boom")), \
                 mock.patch.object(fm, "from_awc", return_value={"WIII": {"raw": "METAR WIII 080230Z=", "obs": "x", "_t": NOW}}), \
                 quiet():
                fm.main(out)
            doc = json.loads(out.read_text())
        self.assertEqual(doc["stations"]["WIII"]["source"], "NOAA AWC")
        self.assertNotIn("_t", doc["stations"]["WIII"])
        self.assertEqual(doc["missing"], ["WADD"])

    def test_reads_icao_list_from_airports_json(self):
        icaos = fm.airport_icaos()
        self.assertGreaterEqual(len(icaos), 100)
        self.assertEqual(len(icaos), len(set(icaos)))


if __name__ == "__main__":
    unittest.main()
