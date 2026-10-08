"""Assemble the standalone dashboard.

Usage:
  python3 scripts/build.py            # writes index.html (full HTML document)
  python3 scripts/build.py --fragment out.html   # body-only fragment (for hosts that add their own <html> skeleton)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

template = (ROOT / "src" / "dashboard.html").read_text(encoding="utf-8")
provinces = json.loads((ROOT / "data" / "provinces.json").read_text(encoding="utf-8"))

page = (
    template
    .replace("/*__PROVINCES__*/null", json.dumps(provinces, separators=(",", ":")))
)

if len(sys.argv) == 3 and sys.argv[1] == "--fragment":
    pathlib.Path(sys.argv[2]).write_text(page, encoding="utf-8")
else:
    doc = (
        '<!doctype html>\n<html lang="id">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + page.replace("<div class=\"app\">", "</head>\n<body>\n<div class=\"app\">", 1)
        + "\n</body>\n</html>\n"
    )
    (ROOT / "index.html").write_text(doc, encoding="utf-8")
