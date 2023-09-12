from typing import Optional
from zoneinfo import ZoneInfo

from rest_food.translation import translate_lazy as _
import dataclasses


DT_DB_FORMAT = '%Y-%m-%d %H:%M:%S'
""" Message.dt_published stored datetime as string rather than mongo time. 
"""

MESSAGE_UI_DT_TIME_FORMAT = '%d-%m %H:%M'


@dataclasses.dataclass
class CountryData:
    code: str
    name: str
    in_name: Optional[str]


@dataclasses.dataclass
class CityData:
    country_code: str
    code: str
    name: str
    for_name: str


@dataclasses.dataclass
class Location:
    country: CountryData
    city: Optional[CityData]


LANG_TO_NAME = [
    ('be', 'Беларуская мова'),
    ('uk', 'Українська мова'),
    ('ru', 'Русский язык'),
    ('pl', 'Język polski'),
    ('lt', 'Lietuvių kalba'),
    ('en', 'English language')
]

COUNTRIES = [
    CountryData('by', _('Belarus'), _('in-Belarus')),
    CountryData('pl', _('Poland'), _('in-Poland')),
    CountryData('lt', _('Lithuania'), _('in-Lithuania')),
    CountryData('other', _('Other'), None),
]


CITIES = [
    CityData('by', 'minsk', _('Minsk'), _('for-Minsk')),
    CityData('pl', 'warszawa', _('Warszawa'), _('for-Warszawa')),
    CityData('lt', 'vilnius', _('Vilnius'), _('for-Vilnius')),
]

COUNTRY_DICT = {x.code: x for x in COUNTRIES}
CITY_DICT = {x.code: x for x in CITIES}
TIMEZONE_DICT = {
    'by': ZoneInfo('Europe/Minsk'),
    'pl': ZoneInfo('Europe/Warsaw'),
    'lt': ZoneInfo('Europe/Vilnius'),
}
