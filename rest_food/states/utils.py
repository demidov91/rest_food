import dataclasses
import logging
import re
from decimal import Decimal
from typing import Tuple, Optional

from requests import Session

from rest_food.entities import User, Message, UserInfoField
from rest_food.db import get_supply_editing_message, get_supply_message_record
from rest_food.exceptions import ValidationError
from rest_food.settings import YANDEX_TOKEN
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)
YANDEX_BBOX_FOR_BELARUS = '23.579,51.5~32.6,56.2'
YANDEX_BBOX_FOR_MINSK = '27.4,53.83~27.7,54'


def _message_to_text(message: Message):
    text_message = '\n'.join([x for x in message.products if x])

    if message.take_time:
        text_message += _('\nTime: {}').format(message.take_time)

    return text_message


def build_active_food_message(user: User):
    if not user.editing_message_id:
        raise ValueError("Active message wasn't defined.")

    message = get_supply_editing_message(user)

    return _message_to_text(message)


def build_food_message_by_id(*, user, message_id):
    return _message_to_text(get_supply_message_record(user=user, message_id=message_id))


def build_demand_description(user: User) -> str:
    message = _('{} will take the food.\n').format(user.info[UserInfoField.NAME.value])
    is_provided_contact_info = False

    if user.info.get(UserInfoField.PHONE.value):
        message += _('Phone: {}\n').format(user.info[UserInfoField.PHONE.value])
        is_provided_contact_info = True

    if (
            user.info.get(UserInfoField.USERNAME.value) and
            user.info.get(UserInfoField.DISPLAY_USERNAME.value)
    ):
        message += _('Telegram: @{}\n').format(user.info[UserInfoField.USERNAME.value])
        is_provided_contact_info = True

    if not is_provided_contact_info:
        message += _('No contact info was provided.\n')

    return message


def validate_phone_number(text):
    if len(text) > 100:
        raise ValidationError(_('Please, provide only pone number.'))

    number_of_digits = len(re.findall(r'\d', text))
    if number_of_digits < 7:
        raise ValidationError(_('This is not a valid phone number.'))


@dataclasses.dataclass
class GeoCoderResult:
    latitude: Decimal
    longitude: Decimal
    is_sure: bool


_http_session = Session()


def _call_yandex_geocoder(address: str) -> Optional[GeoCoderResult]:
    response = _http_session.get(
        f'https://geocode-maps.yandex.ru/1.x/?'
        f'apikey={YANDEX_TOKEN}&'
        f'geocode={address}&'
        f'format=json&'
        f'bbox={YANDEX_BBOX_FOR_MINSK}'
    )

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
        results_count = (
            data['response']['GeoObjectCollection']
            ['metaDataProperty']['GeocoderResponseMetaData']['found']
        )
    except KeyError as e:
        logger.warning(
            "Can't get 'found' data in geocoder response. Key (%s) lost. Content below:%s",
            e, data
        )
        return None

    if results_count == 0:
        return None

    try:
        coordinates_string = (
            data['response']['GeoObjectCollection']
            ['featureMember'][0]['GeoObject']['Point']['pos']
        )
        longiture, latitude = coordinates_string.split()
        latitude = Decimal(latitude)
        longiture = Decimal(longiture)

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

    return GeoCoderResult(latitude=latitude, longiture=longiture, is_sure=results_count == 1)


def get_coordinates(address: str) -> Optional[Tuple[Decimal, Decimal]]:
    data = _call_yandex_geocoder(address)
    if data is None:
        return None

    if not data.is_sure and 'Минск' not in address and 'Мінск' not in address:
        address = 'Минск ' + address

    data = _call_yandex_geocoder(address)
    return data and (data.latitude, data.longitude)
