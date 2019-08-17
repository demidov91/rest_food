import gettext
import logging
import os
from contextvars import ContextVar
from functools import partial
from json import JSONEncoder


from telegram.utils import request as tg_request

from speaklater import make_lazy_gettext, is_lazy_string

from rest_food.settings import BASE_DIR


_active_language = ContextVar('active_language', default='ru')
_translations = {}
LOCALE_DIR = os.path.join(BASE_DIR, 'locale')
logger = logging.getLogger(__name__)


def set_language(lang_code: str):
    if not lang_code or len(lang_code) < 2:
        return

    lang_code = lang_code[:-2]
    if lang_code in ('be', 'ru'):
        _active_language.set(lang_code)


def get_translation(language_code: str):
    if language_code not in _translations:
        if language_code == 'en':
            _translations[language_code] = gettext.NullTranslations()

        else:
            _translations[language_code] = gettext.translation(
                'messages', localedir=LOCALE_DIR, languages=[language_code]
            )

    return _translations[language_code]


def translate(text:str) -> str:
    return get_translation(_active_language.get()).gettext(text)


translate_lazy = make_lazy_gettext(lambda: translate)


class LazyAwareJsonEncoder(JSONEncoder):
    def default(self, o):
        if is_lazy_string(o):
            return str(o)

        return super().encode(o)


def hack_telegram_json_dumps():
    tg_request.json.dumps = partial(tg_request.json.dumps, cls=LazyAwareJsonEncoder)
    logger.info("Telegram json.dumps is monkeypatched.")
