"""Build data/airports.json from the OurAirports open dataset (public domain).

Selection: Indonesian airports that are not closed, have an IATA code, and either
have scheduled service or are classed as medium/large airports. Airports already
in data/airports.json are always kept, with their hand-written name, city,
province and hub flag; coordinates and ICAO codes are refreshed from OurAirports.

Usage:
  python3 scripts/prepare_airports.py airports.csv regions.csv data/airports.json
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


def main(airports_csv, regions_csv, out_path):
    out = pathlib.Path(out_path)
    curated = {a[0]: a for a in json.loads(out.read_text(encoding="utf-8"))} if out.exists() else {}
    regions = {r["code"]: r["name"] for r in csv.DictReader(open(regions_csv, encoding="utf-8")) if r["iso_country"] == "ID"}

    rows = [r for r in csv.DictReader(open(airports_csv, encoding="utf-8"))
            if r["iso_country"] == "ID" and r["type"] != "closed" and r["iata_code"]]
    by_iata = {r["iata_code"]: r for r in rows}
    wanted = {r["iata_code"] for r in rows
              if r["scheduled_service"] == "yes" or r["type"] in ("medium_airport", "large_airport")}
    missing = sorted(set(curated) - set(by_iata))
    if missing:
        sys.exit(f"Curated airports not found in OurAirports: {missing}")

    result = []
    for iata in sorted(wanted | set(curated)):
        r = by_iata[iata]
        icao = r["icao_code"] or r["gps_code"]
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
    main(*sys.argv[1:4])
