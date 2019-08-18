import re

from rest_food.entities import User, Message, UserInfoField
from rest_food.db import get_supply_editing_message, get_supply_message_record
from rest_food.exceptions import ValidationError
from rest_food.translation import translate_lazy as _


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
