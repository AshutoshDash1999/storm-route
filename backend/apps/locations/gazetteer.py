"""
US city and ZIP code search over `data/us_zip_codes.json` (GeoNames, CC BY 4.0).

Cities are built by grouping ZIP codes on (city, state); a city's position is
the mean of its ZIP centroids, except for the curated cities in
`apps.demo.us_locations`, which keep their hand-picked coordinates and IDs.
Results use the frontend `Location` shape plus `type`, `city`, `state`,
`county` and `zipCode`.
"""

import bisect
import json
import re
from functools import cache
from pathlib import Path

from apps.demo import us_locations

DATA_FILE = Path(__file__).resolve().parent / 'data' / 'us_zip_codes.json'
MAX_LIMIT = 50

# Spelling variants folded together for matching ("St. Louis" == "Saint Louis")
_ABBREVIATIONS = {'st': 'saint', 'ste': 'sainte', 'ft': 'fort', 'mt': 'mount'}
_ZIP_QUERY = re.compile(r'^(\d{1,5})(?:-\d{0,4})?$')


def normalize(text: str) -> str:
    words = re.sub(r'[^a-z0-9]+', ' ', text.lower()).split()
    return ' '.join(_ABBREVIATIONS.get(w, w) for w in words)


def zip5(zip_code: int | str) -> str:
    return str(zip_code).zfill(5)


class _Index:
    def __init__(self, records: list[dict]):
        curated = {(normalize(loc['label'].rsplit(', ', 1)[0]), loc['label'].rsplit(', ', 1)[1]): loc
                   for loc in us_locations.US_LOCATIONS}

        self.zips: dict[str, dict] = {}
        groups: dict[tuple[str, str], dict] = {}
        for r in records:
            code = zip5(r['zip_code'])
            key = (normalize(r['city']), r['state'])
            group = groups.setdefault(key, {'city': r['city'], 'state': r['state'], 'counties': {},
                                            'zips': [], 'lat': 0.0, 'lng': 0.0})
            group['zips'].append(code)
            group['lat'] += r['latitude']
            group['lng'] += r['longitude']
            group['counties'][r['county']] = group['counties'].get(r['county'], 0) + 1
            self.zips[code] = {
                'id': f'zip-{code}', 'label': f"{r['city']}, {r['state']} {code}",
                'lng': r['longitude'], 'lat': r['latitude'], 'type': 'zip',
                'city': r['city'], 'state': r['state'], 'county': r['county'], 'zipCode': code,
                '_cityKey': key,
            }
        self.zip_codes = sorted(self.zips)

        self.cities: dict[str, dict] = {}
        self.city_by_key: dict[tuple[str, str], dict] = {}
        for key, g in groups.items():
            n = len(g['zips'])
            known = curated.pop(key, None)
            label = known['label'] if known else f"{g['city']}, {g['state']}"
            city = {
                'id': known['id'] if known else us_locations.slug(label), 'label': label,
                'lng': known['lng'] if known else round(g['lng'] / n, 4),
                'lat': known['lat'] if known else round(g['lat'] / n, 4),
                'type': 'city', 'city': label.rsplit(', ', 1)[0], 'state': g['state'],
                'county': max(g['counties'], key=g['counties'].get), 'zipCode': None,
                '_zips': sorted(g['zips']), '_name': key[0], '_curated': known is not None,
            }
            self._add_city(city, key)
        # Curated cities missing from the ZIP data still need to be searchable
        for key, loc in curated.items():
            self._add_city({**loc, 'type': 'city', 'city': key[0].title(), 'state': key[1], 'county': None,
                            'zipCode': None, '_zips': [], '_name': key[0], '_curated': True}, key)

        # Bigger cities (more ZIP codes) first among equally good name matches
        self.ranked = sorted(self.cities.values(), key=lambda c: (not c['_curated'], -len(c['_zips']), c['label']))

    def _add_city(self, city: dict, key: tuple[str, str]):
        if city['id'] in self.cities:  # slug collision ("O'Fallon" vs "Ofallon"): keep the first
            return
        self.cities[city['id']] = city
        self.city_by_key[key] = city


@cache
def index() -> _Index:
    with open(DATA_FILE, encoding='utf-8') as f:
        return _Index(json.load(f))


def public(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if not k.startswith('_')}


def _search_zips(prefix: str, limit: int) -> list[dict]:
    idx = index()
    start = bisect.bisect_left(idx.zip_codes, prefix)
    out = []
    for code in idx.zip_codes[start:start + limit]:
        if not code.startswith(prefix):
            break
        out.append(idx.zips[code])
    return out


def _split_state(query: str) -> list[tuple[str, str | None]]:
    """Ways to read the query: "dallas, tx" / "dallas tx" → name + state, else name only."""
    if ',' in query:
        name, _, state = query.rpartition(',')
        return [(normalize(name), state.strip().upper() or None)]
    readings = []
    words = query.split()
    if len(words) > 1 and len(words[-1]) == 2 and words[-1].isalpha():
        readings.append((normalize(' '.join(words[:-1])), words[-1].upper()))
    readings.append((normalize(query), None))
    return readings


def _match_rank(name: str, q: str) -> int | None:
    if name == q:
        return 0
    if name.startswith(q):
        return 1
    if f' {q}' in f' {name}':  # starts a later word: "springs" → "Colorado Springs"
        return 2
    return None


def _search_cities(query: str, limit: int) -> list[dict]:
    hits: dict[str, tuple] = {}
    for reading, (name, state) in enumerate(_split_state(query)):
        if not name:
            continue
        for order, city in enumerate(index().ranked):
            if state and not city['state'].startswith(state):
                continue
            rank = _match_rank(city['_name'], name)
            if rank is not None and city['id'] not in hits:
                hits[city['id']] = (reading, rank, order, city)
    return [h[3] for h in sorted(hits.values(), key=lambda h: h[:3])[:limit]]


def search(query: str, limit: int = 10) -> list[dict]:
    """Cities by name ("dall", "Dallas, TX") or ZIP codes by prefix ("752", "75201-1234")."""
    query = query.strip()
    limit = max(1, min(limit, MAX_LIMIT))
    m = _ZIP_QUERY.match(query)
    found = _search_zips(m.group(1), limit) if m else _search_cities(query, limit)
    return [public(e) for e in found]


def get(location_id: str) -> dict | None:
    """A city by ID ("dallas-tx") with its ZIP codes, or a ZIP by ID ("zip-75201")."""
    idx = index()
    key = location_id.strip().lower()
    if key.startswith('zip-'):
        entry = idx.zips.get(key[4:])
        return public(entry) if entry else None
    city = idx.cities.get(key)
    return {**public(city), 'zipCodes': city['_zips']} if city else None


def find(text: str) -> dict | None:
    """Exact lookup for free text: ID, "City, ST", or a 5-digit ZIP (ZIP+4 allowed)."""
    text = text.strip()
    m = _ZIP_QUERY.match(text)
    if m and len(m.group(1)) == 5:
        entry = index().zips.get(m.group(1))
        return public(entry) if entry else None
    if ',' in text:
        name, _, state = text.rpartition(',')
        city = index().city_by_key.get((normalize(name), state.strip().upper()))
        if city:
            return public(city)
    found = get(text)
    if found and found['type'] == 'city':
        found.pop('zipCodes')
    return found
