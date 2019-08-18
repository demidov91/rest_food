import logging
from typing import Iterable

from telegram import Bot

from rest_food.db import get_demand_users
from rest_food.entities import Reply, User, Workflow
from rest_food.settings import TELEGRAM_TOKEN_SUPPLY, TELEGRAM_TOKEN_DEMAND
from rest_food.states.utils import (
    build_active_food_message,
    build_food_message_by_id,
    build_demand_description,
)
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


def get_bot(workflow: Workflow):
    if workflow == Workflow.SUPPLY:
        token = TELEGRAM_TOKEN_SUPPLY
    else:
        token = TELEGRAM_TOKEN_DEMAND

    return Bot(token)


def publish_supply_event(user: User):
    text_message = build_active_food_message(user)
    message = Reply(
        text=_('{} can share the following:\n{}').format(user.info["name"], text_message),
        buttons=[[{
            'text': _('Take it'),
            'data': f'take|{user.provider.value}|{user.user_id}|{user.editing_message_id}',
        }, {
            'text': _('Info'),
            'data': f'info|{user.provider.value}|{user.user_id}|{user.editing_message_id}',
        }]],
    )

    for demand_user in get_demand_users():
        send_messages(
            tg_chat_id=int(demand_user.chat_id),
            replies=[message],
            workflow=Workflow.DEMAND
        )


def notify_supply_for_booked(*, supply_user: User, message_id: str, demand_user: User):
    demand_description = build_demand_description(demand_user)
    food_description = build_food_message_by_id(user=supply_user, message_id=message_id)

    message_to_send = _("{}\n\nYour message was:\n\n{}").format(
        demand_description,
        food_description
    )

    send_messages(
        tg_chat_id=int(supply_user.chat_id),
        replies=[Reply(text=message_to_send)],
        workflow=Workflow.SUPPLY,
    )


def send_messages(*, tg_chat_id: int, replies:Iterable[Reply], workflow: Workflow):
    """
    It's intended to be async (vs `build_tg_response`).
    """
    bot = get_bot(workflow)

    for reply in filter(lambda x: x is not None and (x.text or x.coordinates) is not None, replies):
        markup = _build_tg_keyboard(reply.buttons)
        if reply.coordinates:
            bot.send_location(
                tg_chat_id,
                *(float(x) for x in reply.coordinates),
                reply_markup=None if reply.text else markup,
            )

        if reply.text:
            bot.send_message(
                tg_chat_id,
                reply.text,
                reply_markup=markup
            )


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
