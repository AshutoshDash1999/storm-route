"""US city gazetteer, shared with the frontend location picker (frontend/src/lib/us-locations.ts)."""

import re

# (label, lng, lat)
_RAW = [
    ('Albuquerque, NM', -106.6504, 35.0844),
    ('Amarillo, TX', -101.8313, 35.222),
    ('Anchorage, AK', -149.9003, 61.2181),
    ('Atlanta, GA', -84.388, 33.749),
    ('Austin, TX', -97.7431, 30.2672),
    ('Billings, MT', -108.5007, 45.7833),
    ('Birmingham, AL', -86.8025, 33.5186),
    ('Boise, ID', -116.2023, 43.615),
    ('Boston, MA', -71.0589, 42.3601),
    ('Buffalo, NY', -78.8784, 42.8864),
    ('Charlotte, NC', -80.8431, 35.2271),
    ('Cheyenne, WY', -104.8202, 41.14),
    ('Chicago, IL', -87.6298, 41.8781),
    ('Cincinnati, OH', -84.512, 39.1031),
    ('Cleveland, OH', -81.6944, 41.4993),
    ('Columbus, OH', -82.9988, 39.9612),
    ('Dallas, TX', -96.797, 32.7767),
    ('Denver, CO', -104.9903, 39.7392),
    ('Des Moines, IA', -93.6091, 41.5868),
    ('Detroit, MI', -83.0458, 42.3314),
    ('El Paso, TX', -106.485, 31.7619),
    ('Fargo, ND', -96.7898, 46.8772),
    ('Honolulu, HI', -157.8583, 21.3069),
    ('Houston, TX', -95.3698, 29.7604),
    ('Indianapolis, IN', -86.1581, 39.7684),
    ('Jacksonville, FL', -81.6557, 30.3322),
    ('Kansas City, MO', -94.5786, 39.0997),
    ('Las Vegas, NV', -115.1398, 36.1699),
    ('Little Rock, AR', -92.2896, 34.7465),
    ('Los Angeles, CA', -118.2437, 34.0522),
    ('Louisville, KY', -85.7585, 38.2527),
    ('Memphis, TN', -90.049, 35.1495),
    ('Miami, FL', -80.1918, 25.7617),
    ('Milwaukee, WI', -87.9065, 43.0389),
    ('Minneapolis, MN', -93.265, 44.9778),
    ('Nashville, TN', -86.7816, 36.1627),
    ('New Orleans, LA', -90.0715, 29.9511),
    ('New York, NY', -74.006, 40.7128),
    ('Oklahoma City, OK', -97.5164, 35.4676),
    ('Omaha, NE', -95.9345, 41.2565),
    ('Philadelphia, PA', -75.1652, 39.9526),
    ('Phoenix, AZ', -112.074, 33.4484),
    ('Pittsburgh, PA', -79.9959, 40.4406),
    ('Portland, OR', -122.6765, 45.5152),
    ('Rapid City, SD', -103.231, 44.0805),
    ('Reno, NV', -119.8138, 39.5296),
    ('Sacramento, CA', -121.4944, 38.5816),
    ('Salt Lake City, UT', -111.891, 40.7608),
    ('San Antonio, TX', -98.4936, 29.4241),
    ('San Diego, CA', -117.1611, 32.7157),
    ('San Francisco, CA', -122.4194, 37.7749),
    ('Seattle, WA', -122.3321, 47.6062),
    ('Sioux Falls, SD', -96.7311, 43.5446),
    ('Spokane, WA', -117.426, 47.6588),
    ('St. Louis, MO', -90.1994, 38.627),
    ('Tulsa, OK', -95.9928, 36.154),
    ('Wichita, KS', -97.3301, 37.6872),
]


def slug(label: str) -> str:
    return re.sub(r'[^a-z]+', '-', label.lower()).rstrip('-')


US_LOCATIONS = [{'id': slug(label), 'label': label, 'lng': lng, 'lat': lat} for label, lng, lat in _RAW]

_BY_ID = {loc['id']: loc for loc in US_LOCATIONS}
_BY_LABEL = {loc['label'].lower(): loc for loc in US_LOCATIONS}


def find(text: str) -> dict | None:
    """Exact match on id ("dallas-tx") or label ("Dallas, TX"), case-insensitive."""
    key = text.strip().lower()
    return _BY_ID.get(key) or _BY_LABEL.get(key) or _BY_ID.get(slug(key))
