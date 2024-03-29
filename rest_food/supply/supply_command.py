import logging
from typing import List, Optional

from rest_food.communication import (
    notify_demand_for_approved,
    notify_supplier_is_approved,
    notify_supplier_is_declined,
)
from rest_food.enums import SupplyState, SupplyCommand, UserInfoField, MessageState
from rest_food.supply.supply_utils import get_message_caption
from rest_food.translation import translate_lazy as _
from rest_food.decorators import admin_only
from rest_food.db import (
    set_booking_to_cancel,
    list_messages,
    set_info,
    get_user_by_id,
    get_message_demanded_user,
    set_approved_language, set_message_state, get_supply_message_record, deactivate_message_and_unset_booking,
)
from rest_food.entities import Reply, User, Message
from rest_food.supply.supply_reply import build_supply_side_booked_message
from rest_food.common.formatters import (
    build_short_message_text_by_id,
    build_supplier_approved_text,
    build_supplier_declined_text, message_to_text,
)
from rest_food.translation import set_language as set_context_language

logger = logging.getLogger(__name__)


def handle_supply_command(user: User, command_name: SupplyCommand, args: List[str]):
    """
    Handle direct stateless command.

    Returns
    -------
    Reply

    """
    logger.info('Command: %s, args: %s', command_name, args)

    return {
        SupplyCommand.CANCEL_BOOKING: cancel_booking,
        SupplyCommand.APPROVE_BOOKING: approve_booking,
        SupplyCommand.DEACTIVATE_MESSAGE: deactivate_message,
        SupplyCommand.ACTIVATE_MESSAGE: activate_message,
        SupplyCommand.COMPLETE_MESSAGE: complete_message,
        SupplyCommand.LIST_MESSAGES: view_messages,
        SupplyCommand.SHOW_MESSAGE: show_message,
        SupplyCommand.APPROVE_SUPPLIER: approve_supplier,
        SupplyCommand.DECLINE_SUPPLIER: decline_supplier,
        SupplyCommand.SET_LANGUAGE: set_language,
        SupplyCommand.SET_STATE: set_state,
    }[command_name](user, *args)


def cancel_booking(user, booking_id: str):
    set_booking_to_cancel(user, booking_id)
    return Reply(next_state=SupplyState.BOOKING_CANCEL_REASON)


def approve_booking(user: User, booking_id: str):
    notify_demand_for_approved(supply_user=user, message_id=booking_id)
    set_message_state(booking_id, MessageState.APPROVED)
    return Reply(next_state=SupplyState.READY_TO_POST)


def deactivate_message(user: User, message_id: str) -> Reply:
    message = get_supply_message_record(user=user, message_id=message_id)
    if message is None:
        return Reply(_('Sorry, something went wrong.'))

    deactivate_message_and_unset_booking(message_id)
    return _show_deactivated_message(user, message)


def activate_message(user: User, message_id: str) -> Reply:
    message = get_supply_message_record(user=user, message_id=message_id)
    if message is None:
        return Reply(_('Sorry, something went wrong.'))

    set_message_state(message_id, MessageState.PUBLISHED)
    return _show_non_demanded_message(user, message_id)


def complete_message(user: User, message_id: str) -> Reply:
    message = get_supply_message_record(user=user, message_id=message_id)
    if message is None:
        return Reply(_('Sorry, something went wrong.'))

    set_message_state(message_id, MessageState.TAKEN)
    return _show_taken_message(user, message)


def back_to_posting(user):
    return Reply(next_state=SupplyState.READY_TO_POST)


def set_state(user: User, state: Optional[str]=None):
    return Reply(next_state=SupplyState(state))


def _build_message_button(supply_user: User, message: Message):
    return [{
        'text': get_message_caption(supply_user, message),
        'data': SupplyCommand.SHOW_MESSAGE.build(message.message_id)
    }]


def view_messages(user: User):
    messages = list_messages(user)
    buttons = [_build_message_button(user, x) for x in messages]
    buttons.append([{
        'text': _('Go to product posting'),
        'data': SupplyCommand.SET_STATE.build(SupplyState.READY_TO_POST),
    }])
    return Reply(text=_('Last messages'), buttons=buttons)


def _show_demanded_message(user, message_id: str):
    demand_user = get_message_demanded_user(supply_user=user, message_id=message_id)

    return build_supply_side_booked_message(
        demand_user=demand_user, supply_user=user, message_id=message_id
    )


def _show_non_demanded_message(user, message_id: str):
    message = _('Not yet booked.\n\n%s') % build_short_message_text_by_id(
        message_id=message_id
    )

    return Reply(
        text=message,
        buttons=[[
            {
                'text': _('🛑 Deactivate'),
                'data': SupplyCommand.DEACTIVATE_MESSAGE.build(message_id),
            }, {
                'text': _('View all 📋'),
                'data': SupplyCommand.LIST_MESSAGES.build(),
            }
        ]]
    )


def _show_deactivated_message(user: User, message: Message):
    text = '{}\n\n{}'.format(_('Deactivated'), message_to_text(message))

    return Reply(text=text, buttons=[[
        {
            'text': _('🔄 Activate'),
            'data': SupplyCommand.ACTIVATE_MESSAGE.build(message.message_id),
        }, {
            'text': _('View all 📋'),
            'data': SupplyCommand.LIST_MESSAGES.build(),
        }
    ]])


def _show_approved_message(user: User, message: Message):
    text = '{}\n\n{}'.format(_('Booked and approved'), message_to_text(message))

    return Reply(text=text, buttons=[
        [
            {
                'text': _('🛑 Deactivate'),
                'data': SupplyCommand.DEACTIVATE_MESSAGE.build(message.message_id),
            },
            {
                'text': _('Already shared ✅'),
                'data': SupplyCommand.COMPLETE_MESSAGE.build(message.message_id),
            },
        ],
        [
            {
                'text': _('📋 View all'),
                'data': SupplyCommand.LIST_MESSAGES.build(),
            }
        ],
    ])


def _show_taken_message(user: User, message: Message):
    return Reply(
        text='{}\n\n{}'.format(_('Shared food'), message_to_text(message)),
        buttons=[[
            {
                'text': _('📋 View all'),
                'data': SupplyCommand.LIST_MESSAGES.build(),
            }
        ]]
    )


def show_message(user, message_id: str):
    message = get_supply_message_record(user=user, message_id=message_id)
    if message.state is None or message.state == MessageState.PUBLISHED:
        return _show_non_demanded_message(user, message_id)

    if message.state == MessageState.BOOKED:
        return _show_demanded_message(user, message_id)

    if message.state == MessageState.DEACTIVATED:
        return _show_deactivated_message(user, message)

    if message.state == MessageState.APPROVED:
        return _show_approved_message(user, message)

    if message.state == MessageState.TAKEN:
        return _show_taken_message(user, message)


def set_language(user: User, language: str):
    set_approved_language(user, language)
    set_context_language(language)
    return Reply(next_state=SupplyState.READY_TO_POST)


@admin_only
def approve_supplier(user: User, supplier_id: str):
    supply_user = get_user_by_id(supplier_id)
    set_info(supply_user, UserInfoField.IS_APPROVED_SUPPLY, True)
    notify_supplier_is_approved(supply_user)

    return Reply(
        text=build_supplier_approved_text(supply_user),
        buttons=[[{
            'text': _('Nope, decline it'),
            'data': SupplyCommand.DECLINE_SUPPLIER.build(supplier_id),
        }]]
    )


@admin_only
def decline_supplier(user: User, supplier_id: str):
    supply_user = get_user_by_id(supplier_id)
    set_info(supply_user, UserInfoField.IS_APPROVED_SUPPLY, False)
    notify_supplier_is_declined(supply_user)

    return Reply(
        text=build_supplier_declined_text(supply_user),
        buttons=[[{
            'text': _('Sorry, approve it'),
            'data': SupplyCommand.APPROVE_SUPPLIER.build(supplier_id),
        }]]
    )
