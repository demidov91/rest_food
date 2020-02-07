import logging
from typing import List

from rest_food.communication import (
    notify_demand_for_approved,
    notify_supplier_is_approved,
    notify_supplier_is_declined,
)
from rest_food.translation import translate_lazy as _
from rest_food.decorators import admin_only
from rest_food.db import (
    set_booking_to_cancel,
    list_messages,
    get_user,
    set_info,
    get_user_by_id,
    get_message_demanded_user,
)
from rest_food.entities import Reply, SupplyState, User, Provider, Workflow, Message, SupplyCommand, \
    UserInfoField
from rest_food.states.supply_reply import build_supply_side_booked_message
from rest_food.states.formatters import (
    build_short_message_text_by_id,
    build_supplier_approved_text,
    build_supplier_declined_text,
)
from rest_food.states.utils import db_time_to_user


logger = logging.getLogger(__name__)


def handle_supply_command(user: User, command_name: str, args: List[str]):
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
        SupplyCommand.BACK_TO_POSTING: back_to_posting,
        SupplyCommand.LIST_MESSAGES: view_messages,
        SupplyCommand.SHOW_DEMANDED_MESSAGE: show_demanded_message,
        SupplyCommand.SHOW_NON_DEMANDED_MESSAGE: show_non_demanded_message,
        SupplyCommand.APPROVE_SUPPLIER: approve_supplier,
        SupplyCommand.DECLINE_SUPPLIER: decline_supplier,
    }[command_name](user, *args)


def cancel_booking(user, booking_id: str):
    set_booking_to_cancel(user, booking_id)
    return Reply(next_state=SupplyState.BOOKING_CANCEL_REASON)


def approve_booking(user: User, booking_id: str):
    notify_demand_for_approved(supply_user=user, message_id=booking_id)
    return Reply(next_state=SupplyState.READY_TO_POST)


def back_to_posting(user):
    return Reply(next_state=SupplyState.READY_TO_POST)


def _get_demanded_message_button(message: Message):
    return [{
        'text': _('%s (booked)') % db_time_to_user(message.dt_published, '%d-%m %H:%M'),
        'data': f'c|{SupplyCommand.SHOW_DEMANDED_MESSAGE}|{message.message_id}'
    }]


def _get_non_demanded_message_button(message: Message):
    return [{
        'text': _('%s (not booked)') % db_time_to_user(message.dt_published, '%d-%m %H:%M'),
        'data': f'c|{SupplyCommand.SHOW_NON_DEMANDED_MESSAGE}|{message.message_id}'
    }]


def view_messages(user):
    messages = list_messages(user)
    buttons = [
        _get_demanded_message_button(x) if x.demand_user_id else _get_non_demanded_message_button(x)
        for x in messages
    ]
    buttons.append([{
        'text': _('Go to product posting'),
        'data': f'c|{SupplyCommand.BACK_TO_POSTING}'
    }])
    return Reply(text=_('Last messages'), buttons=buttons)


def show_demanded_message(user, message_id: str, demand_provider: str=None, demand_user_id: str=None):
    """

    Parameters
    ----------
    user
    message_id
    demand_provider: deprecated
    demand_user_id: deprecated
    """

    demand_user = get_message_demanded_user(supply_user=user, message_id=message_id)

    return build_supply_side_booked_message(
        demand_user=demand_user, supply_user=user, message_id=message_id
    )


def show_non_demanded_message(user, message_id: str):
    message = _('Not yet booked.\n\n%s') % build_short_message_text_by_id(
        message_id=message_id
    )

    return Reply(
        text=message,
        buttons=[[{
            'text': _('View all messages'),
            'data': f'c|{SupplyCommand.LIST_MESSAGES}',
        }]]
    )


@admin_only
def approve_supplier(user: User, supplier_id: str):
    supply_user = get_user_by_id(supplier_id)
    set_info(supply_user, UserInfoField.IS_APPROVED_SUPPLY, True)
    notify_supplier_is_approved(supply_user)

    return Reply(
        text=build_supplier_approved_text(supply_user),
        buttons=[[{
            'text': _('Nope, decline it'),
            'data': f'c|{SupplyCommand.DECLINE_SUPPLIER}|{supplier_id}'
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
            'data': f'c|{SupplyCommand.APPROVE_SUPPLIER}|{supplier_id}'
        }]]
    )
