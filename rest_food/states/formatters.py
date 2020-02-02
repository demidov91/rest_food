"""
This module methods are supposed to return strings.
"""

from rest_food.db import get_supply_editing_message, get_supply_message_record
from rest_food.entities import Message, User, UserInfoField, translate_social_status_string
from rest_food.translation import translate_lazy as _


def message_to_text(message: Message) -> str:
    text_message = '\n'.join([x for x in message.products if x])

    if message.take_time:
        text_message += _('\nTime: {}').format(message.take_time)

    return text_message


def build_active_food_message(user: User) -> str:
    if not user.editing_message_id:
        raise ValueError("Active message wasn't defined.")

    message = get_supply_editing_message(user)
    return message_to_text(message)


def build_short_message_text_by_id(*, user: User, message_id: str) -> str:
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
    food_description = build_short_message_text_by_id(user=supply_user, message_id=message_id)

    return _("{}\n\nYour message was:\n\n{}").format(
        demand_description,
        food_description
    )


def build_supply_user_description(user: User):
    return _(
        "Restaurant name: {name}\n"
        "Address: {address}\n"
        "Phone: {phone}"
    ).format(
        name=user.info[UserInfoField.NAME.value],
        address=user.info[UserInfoField.ADDRESS.value],
        phone=user.info[UserInfoField.PHONE.value],
    )


def build_demand_side_full_message_text(supply_user: User, message: Message) -> str:
    return _("{}\n\n\n{}").format(
        build_supply_user_description(supply_user),
        message_to_text(message),
    )


def build_demand_side_full_message_text_by_id(supply_user: User, message_id: str) -> str:
    return build_demand_side_full_message_text(
        supply_user, get_supply_message_record(user=supply_user, message_id=message_id)
    )


def _introduce_new_user(user: User):
    if user.info.get(UserInfoField.USERNAME.value):
        return _('User @%s') % user.info[UserInfoField.value]

    return _('New user')


def build_new_supplier_notification_text(supply_user: User):
    return _('%s wants to join as a supplier. Provided description is:\n\n%s') % (
        _introduce_new_user(supply_user),
        build_supply_user_description(supply_user)
    )


def build_supplier_approved_text(user: User):
    return _('%s was APPROVED as a supplier. Provided description was:\n\n%s\n\nDB id: %s') % (
        _introduce_new_user(user),
        build_supply_user_description(user),
        user.id,
    )


def build_supplier_declined_text(user: User):
    return _('%s was DECLINED as a supplier. Provided description was:\n\n%s\n\nDB id: %s') % (
        _introduce_new_user(user),
        build_supply_user_description(user),
        user.id,
    )
