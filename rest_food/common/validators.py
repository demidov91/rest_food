import logging
import re
from typing import Optional, Type
from enum import Enum

from rest_food.exceptions import ValidationError
from rest_food.translation import translate_lazy as _

logger = logging.getLogger(__name__)


def validate_phone_number(text):
    if len(text) > 100:
        raise ValidationError(_('Please, provide only pone number.'))

    number_of_digits = len(re.findall(r'\d', text))
    if number_of_digits < 7:
        raise ValidationError(_('This is not a valid phone number.'))


def optional_text_to_command(text: Optional[str], the_enum: Type[Enum]) -> Optional[Enum]:
    if not (text and text.startswith('/')):
        return None

    like_command = text[1:]
    try:
        return the_enum(like_command)
    except ValueError:
        logger.warning(f'{text} is not valid {the_enum}')
        return None

