"""
Rebuild apps/locations/data/us_zip_codes.json from the GeoNames US postal code dump.

    python scripts/build_us_zip_codes.py            # downloads US.zip
    python scripts/build_us_zip_codes.py US.txt     # or use a local copy

Source: https://download.geonames.org/export/zip/ (CC BY 4.0, © GeoNames).

Output is a JSON array, one record per line:
    {"zip_code": 501, "latitude": 40.922326, "longitude": -72.637078,
     "city": "Holtsville", "state": "NY", "county": "Suffolk"}
`zip_code` is an integer, so leading zeros are dropped; readers pad it to 5 digits.
"""

import csv
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

SOURCE_URL = 'https://download.geonames.org/export/zip/US.zip'
OUT = Path(__file__).resolve().parent.parent / 'apps' / 'locations' / 'data' / 'us_zip_codes.json'


def read_source(argv: list[str]) -> str:
    if len(argv) > 1:
        return Path(argv[1]).read_text(encoding='utf-8')
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        archive = zipfile.ZipFile(io.BytesIO(resp.read()))
    return archive.read('US.txt').decode('utf-8')


def main(argv: list[str]) -> None:
    records = []
    for cols in csv.reader(io.StringIO(read_source(argv)), delimiter='\t'):
        zip_code, city, state, county, lat, lng = cols[1], cols[2], cols[4], cols[5], cols[9], cols[10]
        if not (zip_code.isdigit() and city and state and lat and lng):
            continue
        records.append({
            'zip_code': int(zip_code),
            'latitude': round(float(lat), 6),
            'longitude': round(float(lng), 6),
            'city': city,
            'state': state,
            'county': county,
        })
    records.sort(key=lambda r: r['zip_code'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ',\n'.join('  ' + json.dumps(r, ensure_ascii=False) for r in records)
    OUT.write_text(f'[\n{lines}\n]\n', encoding='utf-8')
    print(f'Wrote {len(records)} ZIP codes to {OUT}')


if __name__ == '__main__':
    main(sys.argv)
