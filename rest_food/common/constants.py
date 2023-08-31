from typing import Optional

from rest_food.translation import translate_lazy as _
from rest_food.translation import pgettext
import dataclasses


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


LANG_TO_NAME = [
    ('be', 'Беларуская мова'),
    ('uk', 'Українська мова'),
    ('ru', 'Русский язык'),
    ('pl', 'Język polski'),
    ('lt', 'Lietuvių kalba'),
    ('en', 'English language')
]

COUNTRIES = [
    CountryData('by', _('Belarus'), pgettext('in', 'Belarus')),
    CountryData('pl', _('Poland'), pgettext('in', 'Poland')),
    CountryData('lt', _('Lithuania'), pgettext('in', 'Lithuania')),
    CountryData('other', _('Other'), None),
]


CITIES = [
    CityData('by', 'minsk', _('Minsk'), pgettext('for', 'Minsk')),
    CityData('pl', 'warszawa', _('Warszawa'), pgettext('for', 'Warszawa')),
    CityData('lt', 'vilnius', _('Vilnius'), pgettext('for', 'Vilnius')),
]

