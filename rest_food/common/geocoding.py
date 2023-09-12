import dataclasses
import logging
from enum import Enum
from decimal import Decimal
from typing import Optional, List

from requests import Session
from requests.exceptions import ConnectionError

from rest_food.common.constants import Location, CountryData
from rest_food.settings import YANDEX_API_KEY
from rest_food.settings import GOOGLE_API_KEY
from rest_food.translation import switch_language

logger = logging.getLogger(__name__)


class YandexBBox(Enum):
    BELARUS = '23.579,51.5~32.6,56.2'
    MINSK = '27.4,53.83~27.7,54'


class GoogleBounds(Enum):
    WARSZAWA = '52,20.5|52.5,21.3'
    POLAND = '49.13,14.3|55,24.5'


@dataclasses.dataclass
class GeoCoderResult:
    latitude: Decimal
    longitude: Decimal
    is_sure: bool


class Geocoder:
    def __init__(self):
        self._http_session = Session()

    def get_bounds(self, country: CountryData):
        raise NotImplemented

    def call_geocoder(self, address: str, bounds=None):
        raise NotImplemented

    def geocode(self, address: str, country: Optional[CountryData]=None) -> Optional[GeoCoderResult]:
        return self.call_geocoder(address, country and self.get_bounds(country))


class YandexGeocoder(Geocoder):
    def get_bounds(self, country: CountryData):
        if country.code == 'by':
            return YandexBBox.BELARUS

        return None

    def call_geocoder(self, address: str, bbox: Optional[YandexBBox]) -> Optional[GeoCoderResult]:
        logger.info('Geocode %s for %s', address, bbox.name)
        params = {
            'apikey': YANDEX_API_KEY,
            'geocode': address,
            'rspn': 1,
            'format': 'json',
        }
        if bbox is not None:
            params['bbox'] = bbox.value

        try:
            response = self._http_session.get('https://geocode-maps.yandex.ru/1.x/', params=params, timeout=5)
        except ConnectionError:
            logger.exception('Connection error while geocode.')
            return None

        if response.status_code != 200:
            logger.warning(
                'Geocoder API %s status code. Content below:\n%s',
                response.status_code,
                response.content
            )
            return None

        try:
            data = response.json()
        except:
            logger.warning('Non-json geocoder response. Content below:%s', response.content)
            return None

        try:
            results_count = int(
                data['response']['GeoObjectCollection']
                ['metaDataProperty']['GeocoderResponseMetaData']['found']
            )
        except KeyError as e:
            logger.warning(
                "Can't get 'found' data in geocoder response. Key (%s) lost. Content below:%s",
                e, data
            )
            return None
        except ValueError:
            logger.warning("Unexpected 'found' number format. Content below:%s", data)
            return None


        if results_count == 0:
            return None

        try:
            coordinates_string = (
                data['response']['GeoObjectCollection']
                ['featureMember'][0]['GeoObject']['Point']['pos']
            )
            longitude, latitude = coordinates_string.split()
            latitude = Decimal(latitude)
            longitude = Decimal(longitude)

        except KeyError as e:
            logger.warning(
                "Can't get 'pos' key in geocoder response. Key (%s) lost. Content below:\n%s",
                e, data
            )
            return None
        except (ArithmeticError, ValueError):
            logger.warning(
                "Can't get coordinates: %s",
                data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
            )
            return None

        return GeoCoderResult(latitude=latitude, longitude=longitude, is_sure=results_count == 1)


class GoogleGeocoder(Geocoder):
    def get_bounds(self, country) -> Optional[GoogleBounds]:
        if country is None:
            return None

        if country.code == 'pl':
            return GoogleBounds.POLAND

    def call_geocoder(self, address: str, bounds: Optional[GoogleBounds]) -> Optional[GeoCoderResult]:
        logger.info('Geocode %s for %s by Google API.', address, bounds.name)
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'address': address,
            'key': GOOGLE_API_KEY,
        }
        if bounds is not None:
            params['bounds'] = bounds.value

        logger.debug('Making geocoding call with bounds %s', params.get('bounds'))

        try:
            response = self._http_session.get(url, params=params, timeout=5)
        except ConnectionError:
            logger.exception('Connection error while geocode.')
            return None

        if response.status_code != 200:
            logger.warning(
                'Geocoder API %s status code. Content below:\n%s',
                response.status_code,
                response.content
            )
            return None

        try:
            data = response.json()
        except:
            logger.warning('Non-json geocoder response. Content below:%s', response.content)
            return None

        if 'results' not in data or len(data['results']) == 0:
            logger.info('No data found.', extra={'bounds': bounds.name})
            return None

        location = data['results'][0]['geometry']['location']

        return GeoCoderResult(
            latitude=Decimal(location['lat']), longitude=Decimal(location['lng']), is_sure=len(data['results']) == 1,
        )


def get_coordinates(address: str, location: Optional[Location]=None) -> Optional[List[Decimal]]:
    if location is not None:
        if location.city is not None:
            with switch_language('en'):
                address = f'{location.city.name}, {address}'

    if location and location.country.code == 'by':
        geocoder = YandexGeocoder()

    else:
        geocoder = GoogleGeocoder()

    geocoded = geocoder.geocode(address, country=location and location.country)
    return geocoded and [geocoded.latitude, geocoded.longitude]
