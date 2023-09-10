from contextlib import contextmanager
from typing import Optional
from zoneinfo import ZoneInfo

from rest_food.entities import User
from rest_food.enums import UserInfoField
from rest_food.translation import switch_language
from rest_food.common.constants import COUNTRIES, CITY_DICT, CountryData, TIMEZONE_DICT


@contextmanager
def user_language(user):
    with switch_language(user.get_info_field(UserInfoField.LANGUAGE)):
        yield


def get_user_country(user: User) -> Optional[CountryData]:
    location_code = user.get_info_field(UserInfoField.LOCATION)
    if not location_code:
        return None

    country_city = location_code.split(':')
    if len(country_city) == 2:
        return CITY_DICT[country_city[1]].country

    return COUNTRIES[country_city[0]]


def get_user_timezone(user: User) -> Optional[ZoneInfo]:
    country = get_user_country(user)
    return country and TIMEZONE_DICT[country.code]

