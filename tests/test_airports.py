"""Checks on data/airports.json and scripts/prepare_airports.py."""
import contextlib
import csv
import io
import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_airports as pa  # noqa: E402

AIRPORTS = json.loads((ROOT / "data" / "airports.json").read_text(encoding="utf-8"))


class AirportsData(unittest.TestCase):
    def test_rows_are_well_formed(self):
        for row in AIRPORTS:
            iata, icao, name, city, prov, lat, lon, zone, hub = row
            with self.subTest(iata=iata):
                self.assertRegex(iata, r"^[A-Z]{3}$")
                self.assertRegex(icao, r"^W[A-Z]{3}$")
                self.assertTrue(name and city and prov)
                self.assertTrue(-11.5 <= lat <= 6.5 and 94 <= lon <= 141.5, "outside Indonesia")
                self.assertIn(zone, ("WIB", "WITA", "WIT"))
                self.assertIn(hub, (0, 1))

    def test_codes_are_unique(self):
        for col in (0, 1):
            codes = [r[col] for r in AIRPORTS]
            self.assertEqual(len(codes), len(set(codes)))

    def test_zone_matches_longitude_roughly(self):
        # WIB is west of ~116°E, WIT east of ~124°E; a wrong zone usually shows up here.
        for iata, *_, lon, zone, _ in AIRPORTS:
            with self.subTest(iata=iata):
                if zone == "WIB":
                    self.assertLess(lon, 116.5)
                if zone == "WIT":
                    self.assertGreater(lon, 124)


class PrepareAirports(unittest.TestCase):
    HEADER = ["id", "ident", "type", "name", "latitude_deg", "longitude_deg", "elevation_ft", "continent",
              "iso_country", "iso_region", "municipality", "scheduled_service", "icao_code", "iata_code",
              "gps_code", "local_code", "home_link", "wikipedia_link", "keywords"]

    def write_csvs(self, tmp, rows):
        airports = pathlib.Path(tmp) / "airports.csv"
        with open(airports, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, self.HEADER)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in self.HEADER})
        regions = pathlib.Path(tmp) / "regions.csv"
        regions.write_text('code,iso_country,name\nID-JK,ID,Jakarta Raya\nID-BA,ID,Bali\nID-PA,ID,Papua\n'
                           'ID-NT,ID,"Nusa Tenggara Timur (East Nusa Tenggara)"\n', encoding="utf-8")
        return airports, regions

    def base(self, **kw):
        row = dict(iso_country="ID", type="medium_airport", scheduled_service="yes", latitude_deg="-6.2",
                   longitude_deg="106.9", iso_region="ID-JK", municipality="Jakarta")
        row.update(kw)
        return row

    def test_selection_zones_and_curated_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            airports, regions = self.write_csvs(tmp, [
                self.base(iata_code="HLP", icao_code="WIHH", name="Halim Perdanakusuma International Airport"),
                self.base(iata_code="DPS", icao_code="WADD", name="I Gusti Ngurah Rai International Airport",
                          iso_region="ID-BA", latitude_deg="-8.7", longitude_deg="115.2", municipality="Denpasar-Bali Island"),
                self.base(iata_code="XXA", icao_code="WAXA", name="Tiny Airport", type="small_airport",
                          scheduled_service="no", iso_region="ID-PA"),
                self.base(iata_code="XXC", icao_code="WAXC", name="Closed Airport", type="closed", iso_region="ID-PA"),
                self.base(iata_code="KOE", icao_code="", gps_code="WATT", name="El Tari Airport",
                          iso_region="ID-NT", latitude_deg="-10.17", longitude_deg="123.67", municipality="Kupang"),
            ])
            out = pathlib.Path(tmp) / "airports.json"
            out.write_text(json.dumps([["HLP", "WIHH", "Halim (kurasi)", "Jakarta Timur", "DKI Jakarta", 0, 0, "WIB", 1]]))
            with contextlib.redirect_stderr(io.StringIO()):
                pa.main(str(airports), str(regions), str(out))
            rows = {r[0]: r for r in json.loads(out.read_text())}
        self.assertEqual(set(rows), {"HLP", "DPS", "KOE"})  # small/unscheduled and closed are skipped
        self.assertEqual(rows["HLP"][2], "Halim (kurasi)")    # curated name kept
        self.assertEqual(rows["HLP"][8], 1)                   # curated hub kept
        self.assertEqual(rows["HLP"][5], -6.2)                # coordinates refreshed
        self.assertEqual(rows["DPS"][2], "I Gusti Ngurah Rai")
        self.assertEqual(rows["DPS"][7], "WITA")
        self.assertEqual(rows["KOE"][1], "WATT")              # falls back to gps_code
        self.assertEqual(rows["KOE"][4], "Nusa Tenggara Timur")

    def test_unknown_region_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            airports, regions = self.write_csvs(tmp, [self.base(iata_code="ZZZ", icao_code="WZZZ", name="Z", iso_region="ID-XX")])
            with self.assertRaises(SystemExit):
                pa.main(str(airports), str(regions), str(pathlib.Path(tmp) / "out.json"))

    def test_clean_helpers(self):
        self.assertEqual(pa.clean_name("Sultan Hasanuddin International Airport"), "Sultan Hasanuddin")
        self.assertEqual(pa.clean_city("Putussibau-Borneo Island"), "Putussibau")
        self.assertEqual(pa.clean_city("Ba'a - Rote Island"), "Ba'a")
        self.assertTrue(re.match(r"^Wangi", pa.clean_city("Wangi-wangi Island")))


if __name__ == "__main__":
    unittest.main()
