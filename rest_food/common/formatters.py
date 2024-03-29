"""
This module methods are supposed to return strings.
"""
from rest_food.common.constants import CITIES, CITY_DICT, COUNTRY_DICT
from rest_food.db import get_supply_editing_message, get_supply_message_record_by_id
from rest_food.entities import Message, User
from rest_food.enums import UserInfoField
from rest_food.translation import translate_lazy as _


def message_to_text(message: Message) -> str:
    text_message = '\n'.join([x for x in message.products if x])

    if message.take_time:
        text_message += _('\nTime: {}').format(message.take_time)

    return text_message


def build_active_food_message(user: User) -> str:
    message = get_supply_editing_message(user)
    if message is None:
        raise ValueError("Active message wasn't defined.")

    return message_to_text(message)


def build_short_message_text_by_id(message_id: str) -> str:
    return message_to_text(get_supply_message_record_by_id(message_id=message_id))


def build_demand_description(user: User) -> str:
    message = _('{} will take the food.\n').format(user.get_info_field(UserInfoField.NAME))
    is_provided_contact_info = False

    if user.get_info_field(UserInfoField.PHONE):
        message += _('Phone: {}\n').format(user.get_info_field(UserInfoField.PHONE))
        is_provided_contact_info = True

    if (
            user.get_info_field(UserInfoField.USERNAME) and
            user.get_info_field(UserInfoField.DISPLAY_USERNAME)
    ):
        message += _('Telegram: @{}\n').format(user.get_info_field(UserInfoField.USERNAME))
        is_provided_contact_info = True

    if not is_provided_contact_info:
        message += _('No contact info was provided.\n')

    social_status_verbose = user.get_translated_social_status()
    if social_status_verbose is not None:
        message += (
            _('Social status: %s') % social_status_verbose

        )

    return message


def build_demanded_message_text(*, demand_user: User, supply_user: User, message_id: str) -> str:
    demand_description = build_demand_description(demand_user)
    food_description = build_short_message_text_by_id(message_id=message_id)

    return _("{}\n\nYour message was:\n\n{}").format(
        demand_description,
        food_description
    )


def build_supply_user_description(user: User):
    msg = _(
        "Restaurant name: {name}\n"
        "Address: {address}"
    ).format(
        name=user.info[UserInfoField.NAME.value],
        address=user.info[UserInfoField.ADDRESS.value]
    )
    if user.info.get(UserInfoField.PHONE.value):
        msg += _('\nPhone: %s') % user.info[UserInfoField.PHONE.value]

    return msg


def build_demand_side_full_message_text(supply_user: User, message: Message) -> str:
    return "{}\n\n\n{}".format(
        build_supply_user_description(supply_user),
        message_to_text(message),
    )


def build_demand_side_full_message_text_by_id(supply_user: User, message_id: str) -> str:
    return build_demand_side_full_message_text(
        supply_user, get_supply_message_record_by_id(message_id=message_id)
    )


def _introduce_new_user(user: User):
    if user.info.get(UserInfoField.USERNAME.value):
        return _('User @%s') % user.info[UserInfoField.USERNAME.value]

    return _('New user')


def build_new_supplier_notification_text(supply_user: User):
    return (
        _('{user_name} wants to join as a supplier. Provided description is:\n\n{description}').format(
            user_name=_introduce_new_user(supply_user),
            description=build_supply_user_description(supply_user),
        )
    )


def build_supplier_approved_text(user: User):
    return _(
        '{user_name} was APPROVED as a supplier. '
        'Provided description was:\n\n{description}\n\n'
        'DB id: {id}'
    ).format(
        user_name=_introduce_new_user(user),
        description=build_supply_user_description(user),
        id=user.id,
    )


def build_supplier_declined_text(user: User):
    return _(
        '{user_name} was DECLINED as a supplier. '
        'Provided description was:\n\n{description}\n\n'
        'DB id: {id}'
    ).format(
        user_name=_introduce_new_user(user),
        description=build_supply_user_description(user),
        id=user.id,
    )


def location_to_string(location_code: str) -> str:
    if not location_code:
        return '❌'

    country_city = location_code.split(':')
    if len(country_city) == 2:
        return CITY_DICT[country_city[1]].name

    return COUNTRY_DICT[country_city[0]].name


def bold(text: str) -> str:
    return f'<b>{text}</b>'