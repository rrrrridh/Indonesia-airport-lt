"""Simplify the BAKOSURTANAL province GeoJSON and tag each province with its time zone.

Source: https://github.com/superpikar/indonesia-geojson (indonesia-province-simple.json)
Usage: python3 scripts/prepare_provinces.py indonesia-province-simple.json data/provinces.json
"""
import json,sys
d=json.load(open(sys.argv[1]))
names={'IRIAN JAYA TIMUR':'Papua','IRIAN JAYA TENGAH':'Papua','IRIAN JAYA BARAT':'Papua Barat','NUSATENGGARA BARAT':'Nusa Tenggara Barat','PROBANTEN':'Banten','DI. ACEH':'Aceh','DAERAH ISTIMEWA YOGYAKARTA':'DI Yogyakarta','DKI JAKARTA':'DKI Jakarta','BANGKA BELITUNG':'Kep. Bangka Belitung','RIAU':'Riau & Kep. Riau','SULAWESI SELATAN':'Sulawesi Selatan & Barat','KALIMANTAN TIMUR':'Kalimantan Timur & Utara'}
wib={'Aceh','Sumatera Utara','Sumatera Barat','Riau & Kep. Riau','Jambi','Sumatera Selatan','Bengkulu','Lampung','Kep. Bangka Belitung','Banten','DKI Jakarta','Jawa Barat','Jawa Tengah','DI Yogyakarta','Jawa Timur','Kalimantan Barat','Kalimantan Tengah'}
wit={'Maluku','Maluku Utara','Papua','Papua Barat'}
def r(ring):
  out=[]
  for x,y in ring:
    p=[round(x,3),round(y,3)]
    if not out or out[-1]!=p: out.append(p)
  return out if len(out)>=4 else None
feats=[]
for f in d['features']:
  raw=f['properties']['Propinsi']
  n=names.get(raw, raw.title())
  z='WIB' if n in wib else 'WIT' if n in wit else 'WITA'
  g=f['geometry']; polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
  np_=[]
  for poly in polys:
    rings=[q for q in (r(x) for x in poly) if q]
    if rings: np_.append(rings)
  feats.append({'type':'Feature','properties':{'n':n,'z':z},'geometry':{'type':'MultiPolygon','coordinates':np_}})
  print(n,z,file=sys.stderr)
json.dump({'type':'FeatureCollection','features':feats},open(sys.argv[2],'w'),separators=(',',':'))
