import logging
from typing import List

from rest_food.translation import translate_lazy as _
from rest_food.db import set_booking_to_cancel, list_messages, get_supply_message_record, get_user
from rest_food.entities import Reply, SupplyState, User, Provider, Workflow, Message
from rest_food.states.utils import build_demanded_message_text, build_food_message_by_id, db_time_to_user


logger = logging.getLogger(__name__)


class SupplyCommand:
    CANCEL_BOOKING = 'cancel_booking'
    BACK_TO_POSTING = 'back_to_posting'
    LIST_MESSAGES = 'list_messages'
    SHOW_DEMANDED_MESSAGE = 'sdm'
    SHOW_NON_DEMANDED_MESSAGE = 'show_ndm'


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
        SupplyCommand.BACK_TO_POSTING: back_to_posting,
        SupplyCommand.LIST_MESSAGES: view_messages,
        SupplyCommand.SHOW_DEMANDED_MESSAGE: show_demanded_message,
        SupplyCommand.SHOW_NON_DEMANDED_MESSAGE: show_non_demanded_message,
    }[command_name](user, *args)


def cancel_booking(user, booking_id: str):
    set_booking_to_cancel(user, booking_id)
    return Reply(next_state=SupplyState.BOOKING_CANCEL_REASON)


def back_to_posting(user):
    return Reply(next_state=SupplyState.READY_TO_POST)


def _get_demanded_message_button(message: Message):
    return [{
        'text': _('%s (booked)') % db_time_to_user(message.dt_created, '%d-%m %H:%M'),
        'data': f'c|{SupplyCommand.SHOW_DEMANDED_MESSAGE}|{message.message_id}|{message.demand_user_id}'
    }]


def _get_non_demanded_message_button(message: Message):
    return [{
        'text': _('%s (not booked)') % db_time_to_user(message.dt_created, '%d-%m %H:%M'),
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


def show_demanded_message(user, message_id: str, demand_provider: str, demand_user_id: str):
    demand_user = get_user(
        demand_user_id, provider=Provider(demand_provider), workflow=Workflow.DEMAND
    )
    message = build_demanded_message_text(
        demand_user=demand_user, supply_user=user, message_id=message_id
    )

    buttons = [
        [{
            'text': _('Reject'),
            'data': f'c|{SupplyCommand.CANCEL_BOOKING}|{message_id}',
        }],
        [{
            'text': _('View all messages'),
            'data': f'c|{SupplyCommand.LIST_MESSAGES}',
        }],
    ]

    return Reply(text=message, buttons=buttons)


def show_non_demanded_message(user, message_id: str):
    message = _('Not yet booked.\n\n%s') % build_food_message_by_id(
        user=user, message_id=message_id
    )

    return Reply(
        text=message,
        buttons=[[{
            'text': _('View all messages'),
            'data': f'c|{SupplyCommand.LIST_MESSAGES}',
        }]]
    )

