"""Refresh data/airports.json from the OurAirports open dataset (public domain).

The airport list itself is curated: airports that can take at least an ATR 72/42
(and the jet airports for A320/A330/B737), without pioneer strips that only see
Twin Otter/Caravan-class aircraft. OurAirports has no reliable aircraft data, so
this script does not choose airports. It keeps every airport already in
data/airports.json, with its hand-written name, city, province and hub flag, and
refreshes coordinates and ICAO codes. New airports are added by IATA code with
--add; their names come from OurAirports and should be tidied by hand.

Usage:
  python3 scripts/prepare_airports.py airports.csv regions.csv data/airports.json [--add XXX,YYY]
  (airports.csv / regions.csv from https://github.com/davidmegginson/ourairports-data)
"""
import csv
import json
import pathlib
import re
import sys

# Time zone per province (ISO 3166-2:ID code).
ZONE = {
    **dict.fromkeys("AC SU SB RI KR JA SS BE LA BB BT JK JB JT YO JI KB KT".split(), "WIB"),
    **dict.fromkeys("BA NB NT KS KI KU SN SR ST SG SA GO".split(), "WITA"),
    **dict.fromkeys("MA MU PA PB PD PP PS PT".split(), "WIT"),
}
PROVINCE_NAMES = {"ID-JK": "DKI Jakarta", "ID-YO": "DI Yogyakarta", "ID-BB": "Kep. Bangka Belitung"}


def clean_name(name):
    name = re.sub(r"\s+(International\s+)?(Airport|Airfield|Airstrip)$", "", name.strip())
    return re.sub(r"\s+International$", "", name)


def clean_city(city):
    city = re.sub(r"-(Sumatra|Borneo|Celebes|Java|Morotai) Island$", "", city.strip())
    return re.sub(r"\s+-\s+[\w' ]+ Island$", "", city)


def main(airports_csv, regions_csv, out_path, add=()):
    out = pathlib.Path(out_path)
    curated = {a[0]: a for a in json.loads(out.read_text(encoding="utf-8"))} if out.exists() else {}
    with open(regions_csv, encoding="utf-8") as f:
        regions = {r["code"]: r["name"] for r in csv.DictReader(f) if r["iso_country"] == "ID"}
    with open(airports_csv, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)
                if r["iso_country"] == "ID" and r["type"] != "closed" and r["iata_code"]]
    by_iata = {r["iata_code"]: r for r in rows}
    wanted = set(curated) | set(add)
    missing = sorted(wanted - set(by_iata))
    if missing:
        sys.exit(f"Airports not found in OurAirports: {missing}")

    result = []
    for iata in sorted(wanted):
        r = by_iata[iata]
        icao = r["icao_code"] or r["gps_code"]
        if not re.fullmatch(r"W[A-Z]{3}", icao):
            sys.exit(f"No ICAO code for {iata} in OurAirports")
        region = r["iso_region"]
        code = region.split("-")[1]
        if code not in ZONE:
            sys.exit(f"No time zone for region {region} ({iata})")
        prov = PROVINCE_NAMES.get(region) or re.sub(r"\s*\(.*\)$", "", regions.get(region, code))
        lat, lon = round(float(r["latitude_deg"]), 4), round(float(r["longitude_deg"]), 4)
        if iata in curated:
            _, _, name, city, prov, _, _, _, hub = curated[iata]
        else:
            name, city, hub = clean_name(r["name"]), clean_city(r["municipality"]) or clean_name(r["name"]), 0
        result.append([iata, icao, name, city, prov, lat, lon, ZONE[code], hub])

    order = {"WIB": 0, "WITA": 1, "WIT": 2}
    result.sort(key=lambda a: (order[a[7]], -a[5]))  # by zone, then north to south
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("[\n" + ",\n".join(json.dumps(a, ensure_ascii=False) for a in result) + "\n]\n", encoding="utf-8")
    print(f"{len(result)} airports written to {out} ({len(curated)} curated)", file=sys.stderr)


if __name__ == "__main__":
    args = sys.argv[1:]
    add = []
    if "--add" in args:
        i = args.index("--add")
        add = [c.strip().upper() for c in args[i + 1].split(",") if c.strip()]
        del args[i:i + 2]
    main(*args[:3], add=add)
