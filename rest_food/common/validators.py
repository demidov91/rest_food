import logging
import re
from rest_food.exceptions import ValidationError
from rest_food.translation import translate_lazy as _

logger = logging.getLogger(__name__)


def validate_phone_number(text):
    if len(text) > 100:
        raise ValidationError(_('Please, provide only pone number.'))

    number_of_digits = len(re.findall(r'\d', text))
    if number_of_digits < 7:
        raise ValidationError(_('This is not a valid phone number.'))

