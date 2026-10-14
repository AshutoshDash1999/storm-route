import pytest

from apps.locations import gazetteer


def search(client, **params):
    return client.get('/api/locations/search/', params)


def labels(r):
    return [loc['label'] for loc in r.json()['results']]


# Search

def test_search_by_city_prefix_puts_big_cities_first(client):
    r = search(client, q='dall')
    assert r.status_code == 200
    assert r.json()['query'] == 'dall'
    assert labels(r)[0] == 'Dallas, TX'
    assert all(loc['type'] == 'city' for loc in r.json()['results'])


@pytest.mark.parametrize('q', ['Dallas, TX', 'dallas tx', 'DALLAS,tx'])
def test_search_city_with_state(client, q):
    assert labels(search(client, q=q))[0] == 'Dallas, TX'


def test_search_folds_saint_and_st(client):
    assert labels(search(client, q='saint lou'))[0] == 'St. Louis, MO'
    assert labels(search(client, q='st. louis'))[0] == 'St. Louis, MO'


def test_search_matches_later_words(client):
    assert 'Colorado Springs, CO' in labels(search(client, q='springs', limit=50))


def test_search_by_zip_prefix(client):
    results = search(client, q='752', limit=3).json()['results']
    assert [loc['zipCode'] for loc in results] == ['75201', '75202', '75203']
    assert results[0] == {
        'id': 'zip-75201', 'label': 'Dallas, TX 75201', 'type': 'zip', 'city': 'Dallas', 'state': 'TX',
        'county': 'Dallas', 'zipCode': '75201', 'lng': results[0]['lng'], 'lat': results[0]['lat'],
    }


def test_search_zip_keeps_leading_zeros_and_accepts_zip4(client):
    assert labels(search(client, q='00501'))[0] == 'Holtsville, NY 00501'
    assert labels(search(client, q='75201-1234')) == ['Dallas, TX 75201']


def test_search_limit(client):
    assert len(search(client, q='spring', limit=3).json()['results']) == 3


def test_search_no_match_is_empty(client):
    assert search(client, q='zzqx').json()['results'] == []


@pytest.mark.parametrize('params, field', [({}, 'q'), ({'q': '  '}, 'q'), ({'q': 'a', 'limit': 0}, 'limit'),
                                           ({'q': 'a', 'limit': 'x'}, 'limit'), ({'q': 'a', 'limit': 51}, 'limit')])
def test_search_validation(client, params, field):
    r = search(client, **params)
    assert r.status_code == 400
    assert field in r.json()['error']['fields']


# Detail

def test_city_detail_lists_zip_codes(client):
    r = client.get('/api/locations/chicago-il/')
    assert r.status_code == 200
    data = r.json()
    # Curated cities keep their hand-picked coordinates
    assert (data['label'], data['lng'], data['lat']) == ('Chicago, IL', -87.6298, 41.8781)
    assert '60601' in data['zipCodes']


def test_zip_detail(client):
    data = client.get('/api/locations/zip-80202/').json()
    assert (data['type'], data['city'], data['state']) == ('zip', 'Denver', 'CO')


def test_location_not_found(client):
    r = client.get('/api/locations/nowhere-zz/')
    assert r.status_code == 404
    assert r.json()['error']['code'] == 'location_not_found'


# Free-text resolution used by analyze

@pytest.mark.parametrize('text, label', [('75201', 'Dallas, TX 75201'), ('Boulder, CO', 'Boulder, CO'),
                                         ('dallas-tx', 'Dallas, TX'), ('zip-60601', 'Chicago, IL 60601')])
def test_find(text, label):
    assert gazetteer.find(text)['label'] == label


def test_analyze_accepts_zip_codes(client, tomorrow):
    r = client.post('/api/routes/analyze/', {'origin': '75201', 'destination': 'Houston, TX',
                                            'departureAt': tomorrow.isoformat(), 'loadWeightLb': 35000},
                    format='json')
    assert r.status_code == 200
    assert r.json()['trip']['origin']['id'] == 'zip-75201'
    assert set(r.json()['trip']['origin']) == {'id', 'label', 'lng', 'lat'}
