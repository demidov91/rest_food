from typing import Optional

from rest_food.translation import translate_lazy as _
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

