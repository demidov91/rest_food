import pytest
from rest_food.common.constants import COUNTRY_DICT, CITY_DICT, Location
from rest_food.common.geocoding import get_coordinates, GeoCoderResult
from unittest.mock import patch


@pytest.mark.parametrize(
    'in_address, country_code, city_code, expected_address',
    [
        ('ul. Vodołażskiego 98/12', 'pl', 'warszawa', 'Warsaw, ul. Vodołażskiego 98/12'),
        ('Kaunas. Vitautas gv. 96-5', 'lt', None, 'Kaunas. Vitautas gv. 96-5'),
        ('Any name 42', 'other', None, 'Any name 42'),
    ],
)
def test_get_coordinates(in_address, country_code, city_code, expected_address):
    country = COUNTRY_DICT.get(country_code)
    city = CITY_DICT.get(city_code)
    location = None
    if country is not None:
        location = Location(country=country, city=city)

    with patch('rest_food.common.geocoding.Geocoder.geocode', return_value=GeoCoderResult(10, 22, True)) as p:
        coordinates = get_coordinates(in_address, location=location)

    assert coordinates == [10, 22]
    p.assert_called_once_with(expected_address, country=country)
