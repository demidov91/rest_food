import dataclasses
import datetime
import logging
import re
import time
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from requests import Session

from rest_food.entities import User, Message, UserInfoField, translate_social_status_string, \
    DT_FORMAT, Command, Reply, DemandCommandName, SupplyCommand
from rest_food.db import get_supply_editing_message, get_supply_message_record
from rest_food.exceptions import ValidationError
from rest_food.settings import YANDEX_API_KEY
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


class YandexBBox(Enum):
    BELARUS = '23.579,51.5~32.6,56.2'
    MINSK = '27.4,53.83~27.7,54'


def to_local_time(system_time: datetime.datetime):
    """
    No pytz implementation of utc to utc+3 convertion.
    """
    utc_offset = -time.timezone
    target_offset = datetime.timedelta(hours=3) - datetime.timedelta(seconds=utc_offset)
    return system_time + target_offset


def db_time_to_user(db_time: Optional[str], fmt: str) -> str:
    if not db_time:
        return '~~~'

    return to_local_time(datetime.datetime.strptime(db_time, DT_FORMAT)).strftime(fmt)


def message_to_text(message: Message):
    text_message = '\n'.join([x for x in message.products if x])

    if message.take_time:
        text_message += _('\nTime: {}').format(message.take_time)

    return text_message


def build_active_food_message(user: User):
    if not user.editing_message_id:
        raise ValueError("Active message wasn't defined.")

    message = get_supply_editing_message(user)

    return message_to_text(message)


def build_food_message_by_id(*, user, message_id):
    return message_to_text(get_supply_message_record(user=user, message_id=message_id))


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

    social_status_verbose = translate_social_status_string(
        user.info.get(UserInfoField.SOCIAL_STATUS.value)
    )
    if social_status_verbose is not None:
        message += (
            _('Social status: %s') % social_status_verbose

        )

    return message


def build_demanded_message_text(*, demand_user: User, supply_user: User, message_id: str) -> str:
    demand_description = build_demand_description(demand_user)
    food_description = build_food_message_by_id(user=supply_user, message_id=message_id)

    return _("{}\n\nYour message was:\n\n{}").format(
        demand_description,
        food_description
    )


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


def _call_yandex_geocoder(address: str, bbox: YandexBBox) -> Optional[GeoCoderResult]:
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
    response = _http_session.get(url)

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


def geocode(address: str) -> Optional[GeoCoderResult]:
    minsk_data = _call_yandex_geocoder(address, YandexBBox.MINSK)
    if minsk_data and minsk_data.is_sure:
        return minsk_data

    belarus_data = _call_yandex_geocoder(address, YandexBBox.BELARUS)
    if belarus_data and belarus_data.is_sure:
        return belarus_data

    return minsk_data or belarus_data


def get_coordinates(address: str) -> Optional[List[Decimal]]:
    geocoded = geocode(address)
    return geocoded and [geocoded.latitude, geocoded.longitude]


def get_next_command(user: User) -> Command:
    logger.info('User context: %s', user.context)

    return Command(
        name=user.context['next_command'],
        arguments=user.context['arguments'],
    )


def build_demand_command_button(text: str, command: Command):
    return {
        'text': text,
        'data': DemandCommandName(command.name).build(*command.arguments),
    }


def get_demand_back_button(user: User, text: str=_('Back')):
    return build_demand_command_button(text, get_next_command(user))


def build_demand_side_short_message(supply_user: User, message_id: str):
    text_message = build_food_message_by_id(user=supply_user, message_id=message_id)
    return Reply(
        text=_('{} can share the following:\n{}').format(
            supply_user.info[UserInfoField.NAME.value], text_message
        ),
        buttons=[[{
            'text': _('Take it'),
            'data': DemandCommandName.TAKE.build(
                supply_user.provider.value, supply_user.user_id, supply_user.editing_message_id
            ),
        }, {
            'text': _('Info'),
            'data': DemandCommandName.INFO.build(
                supply_user.provider.value, supply_user.user_id, message_id
            )
        }]],
    )


def build_demand_side_full_message_text(supply_user: User, message: Message) -> str:
    return _(
        "Restaurant name: {name}\n"
        "Address: {address}\n"
        "Phone: {phone}\n"
        "\n\n"
        "{products}"
    ).format(
        name=supply_user.info[UserInfoField.NAME.value],
        address=supply_user.info[UserInfoField.ADDRESS.value],
        phone=supply_user.info[UserInfoField.PHONE.value],
        products=message_to_text(message),
    )


def build_supply_side_booked_message(*, demand_user: User, supply_user: User, message_id: str):
    message = build_demanded_message_text(
        demand_user=demand_user, supply_user=supply_user, message_id=message_id
    )

    buttons = [
        [{
            'text': _('Reject'),
            'data': f'c|{SupplyCommand.CANCEL_BOOKING}|{message_id}',
        }, {
            'text': _('Ask to contact'),
            'data': f'c|{SupplyCommand.ASK_TO_CONTACT}|{message_id}|{demand_user.provider.value}|{demand_user.user_id}',
        }, {
            'text': _('Approve'),
            'data': f'c|{SupplyCommand.APPROVE_BOOKING}|{message_id}',
        }],
        [{
            'text': _('View all messages'),
            'data': f'c|{SupplyCommand.LIST_MESSAGES}',
        }],
    ]

    return Reply(text=message, buttons=buttons)
