import logging
from typing import Iterable

from telegram import Bot, Message
from telegram.error import BadRequest

from rest_food.db import get_demand_users, get_user, get_supply_message_record
from rest_food.entities import Reply, User, Workflow, Provider, UserInfoField, DemandCommandName
from rest_food.settings import TELEGRAM_TOKEN_SUPPLY, TELEGRAM_TOKEN_DEMAND
from rest_food.states.supply_command import SupplyCommand
from rest_food.states.utils import (
    build_active_food_message,
    build_food_message_by_id,
    build_demanded_message_text,
    build_demand_side_short_message,
)
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


def get_bot(workflow: Workflow):
    if workflow == Workflow.SUPPLY:
        token = TELEGRAM_TOKEN_SUPPLY
    else:
        token = TELEGRAM_TOKEN_DEMAND

    return Bot(token)


def publish_supply_event(supply_user: User):
    message = build_demand_side_short_message(supply_user, supply_user.editing_message_id)

    for demand_user in get_demand_users():
        send_messages(
            tg_chat_id=int(demand_user.chat_id),
            replies=[message],
            workflow=Workflow.DEMAND
        )


def notify_supply_for_booked(*, supply_user: User, message_id: str, demand_user: User):
    text_to_send = build_demanded_message_text(
        supply_user=supply_user, demand_user=demand_user, message_id=message_id
    )
    buttons_to_send = [
        [{
            'text': _('Reject'),
            'data': f'c|{SupplyCommand.CANCEL_BOOKING}|{message_id}',
        }],
        [{
            'text': _('View all messages'),
            'data': f'c|{SupplyCommand.LIST_MESSAGES}',
        }],
    ]

    send_messages(
        tg_chat_id=int(supply_user.chat_id),
        replies=[Reply(text=text_to_send, buttons=buttons_to_send)],
        workflow=Workflow.SUPPLY,
    )


def notify_demand_for_cancel(*, supply_user: User, message_id: str, message: str):
    message_record = get_supply_message_record(user=supply_user, message_id=message_id)
    if message_record.demand_user_id is None:
        raise ValueError('Demand user is not defined.')

    provider, user_id = message_record.demand_user_id.split('|')
    demand_user = get_user(user_id=user_id, provider=Provider(provider), workflow=Workflow.DEMAND)

    food_description = build_food_message_by_id(user=supply_user, message_id=message_id)
    text_to_send = _(
        'Your request was rejected with the following words:\n%(message)s\n\nRequest was:\n%(food)s'
    ) % {
        'message': message,
        'food': food_description,
    }

    send_messages(
        tg_chat_id=int(demand_user.chat_id),
        replies=[Reply(text=text_to_send)],
        workflow=Workflow.DEMAND,
    )


def send_messages(
        *,
        tg_chat_id: int,
        original_message: Message = None,
        replies: Iterable[Reply],
        workflow: Workflow
):
    """
    It's intended to be async (vs `build_tg_response`).
    """
    bot = get_bot(workflow)
    original_message_should_be_replaced = (
        (original_message and original_message.message_id) is not None
    )

    for reply in filter(lambda x: x is not None and (x.text or x.coordinates) is not None, replies):
        markup = _build_tg_keyboard(reply.buttons)

        if reply.coordinates:
            bot.send_location(
                tg_chat_id,
                *(float(x) for x in reply.coordinates),
                reply_markup=None if reply.text else markup,
            )

        if reply.text:
            if original_message_should_be_replaced and original_message.text is not None:
                method = bot.edit_message_text
                original_message_should_be_replaced = False
            else:
                method = bot.send_message

            try:
                method(
                    chat_id=tg_chat_id,
                    text=reply.text,
                    reply_markup=markup,
                    message_id=original_message and original_message.message_id
                )
            except BadRequest as e:
                if 'the same' in e.message:
                    pass
                else:
                    raise e

        if original_message_should_be_replaced:
            bot.delete_message(chat_id=tg_chat_id, message_id=original_message.message_id)


def build_tg_response(*, chat_id: int, reply: Reply):
    """
    Use it for direct/sync response (vs `send_messages`).
    """
    response = {
        'method': 'sendMessage',
        'chat_id': chat_id,
        'text': reply.text,
    }

    if reply.buttons:
        response['reply_markup'] = _build_tg_keyboard(reply.buttons)

    return response


def _build_tg_keyboard(keyboard):
    if not keyboard:
        return None

    inline_keyboard = [
        [
            _build_tg_keyboard_cell(cell) for cell in row
        ] for row in keyboard
    ]

    return {
        'inline_keyboard': inline_keyboard,
    }


def _build_tg_keyboard_cell(cell):
    if isinstance(cell, dict):
        formatted_cell = {
            'text': cell['text'],
        }

        if 'data' in cell:
            formatted_cell['callback_data'] = cell['data']
        elif 'url' in cell:
            formatted_cell['url'] = cell['url']

        return formatted_cell

    return {
        'text': cell,
        'callback_data': cell,
    }
