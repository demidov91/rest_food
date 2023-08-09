import dataclasses
import logging
from enum import Enum
from decimal import Decimal
from typing import Optional, List

from requests import Session
from requests.exceptions import ConnectionError
from rest_food.settings import YANDEX_API_KEY
from rest_food.settings import GOOGLE_API_KEY


logger = logging.getLogger(__name__)


class YandexBBox(Enum):
    BELARUS = '23.579,51.5~32.6,56.2'
    MINSK = '27.4,53.83~27.7,54'


class GoogleBounds(Enum):
    GDANSK = '54.3,18.5|54.6,18.8'
    WARSZAWA = '52,20.5|52.5,21.3'
    POLAND = '49.13,14.3|55,24.5'


@dataclasses.dataclass
class GeoCoderResult:
    latitude: Decimal
    longitude: Decimal
    is_sure: bool


_http_session = Session()


def _call_yandex_geocoder(address: str, bbox: YandexBBox) -> Optional[GeoCoderResult]:
    """Deprecated."""
    logger.info('Geocode %s for %s', address, bbox.name)
    url = (
        f'https://geocode-maps.yandex.ru/1.x/?'
        f'apikey={YANDEX_API_KEY}&'
        f'geocode={address}&'
        f'bbox={bbox.value}&'
        f'rspn=1&'
        f'format=json'
    )
    logger.debug(url)

    try:
        response = _http_session.get(url, timeout=5)
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


def _call_google_geocoder(address: str, bounds: GoogleBounds) -> Optional[GeoCoderResult]:
    logger.info('Geocode %s for %s by Google API.', address, bounds.name)
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': address,
        'key': GOOGLE_API_KEY,
        'bounds': bounds.value,
    }

    logger.debug('Making geocoding call.', extra={'url': url, 'address': address, 'bounds': bounds.value})

    try:
        response = _http_session.get(url, params=params, timeout=5)
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


def geocode(address: str) -> Optional[GeoCoderResult]:
    last_retrieved = None

    for bounds in GoogleBounds:
        geocoding_data = _call_google_geocoder(address, bounds)
        if geocoding_data is not None:
            last_retrieved = geocoding_data
            if geocoding_data.is_sure:
                break

    return last_retrieved


def get_coordinates(address: str) -> Optional[List[Decimal]]:
    geocoded = geocode(address)
    return geocoded and [geocoded.latitude, geocoded.longitude]
