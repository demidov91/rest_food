import logging
import time
from typing import Iterable

from telegram import Bot, Message
from telegram.error import BadRequest, Unauthorized

from rest_food.db import get_demand_users, get_message_demanded_user
from rest_food.entities import Reply, User, Workflow
from rest_food.message_queue import message_queue
from rest_food.settings import TELEGRAM_TOKEN_SUPPLY, TELEGRAM_TOKEN_DEMAND, STAGE, TEST_TG_CHAT_ID
from rest_food.states.demand_reply import build_demand_side_short_message, \
    build_demand_side_message_by_id
from rest_food.states.supply_reply import build_supply_side_booked_message
from rest_food.states.formatters import build_demand_side_full_message_text_by_id
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


class FakeBot:
    sleep_time = 0.2

    def __init__(self, bot: Bot):
        self._bot = bot

    def _sleep(self):
        logger.warning('Sleep for %s s', self.sleep_time)
        time.sleep(0.2)

    def send_location(self, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            self._bot.send_location(chat_id, *args, **kwargs)
        else:
            self._sleep()

    def edit_message_text(self, text, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            self._bot.edit_message_text(text, chat_id, *args, **kwargs)
        else:
            self._sleep()

    def send_message(self, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            self._bot.send_message(chat_id, *args, **kwargs)
        else:
            self._sleep()

    def delete_message(self, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            self._bot.delete_message(chat_id, *args, **kwargs)
        else:
            self._sleep()

    def set_webhook(self, *args, **kwargs):
        return self._bot.set_webhook(*args, **kwargs)


def get_bot(workflow: Workflow):
    if workflow == Workflow.SUPPLY:
        token = TELEGRAM_TOKEN_SUPPLY
    else:
        token = TELEGRAM_TOKEN_DEMAND

    bot = Bot(token)

    if STAGE != 'live':
        return FakeBot(bot)

    return bot


def publish_supply_event(supply_user: User):
    message = build_demand_side_short_message(supply_user, supply_user.editing_message_id)
    message_queue.push_super_batch(
        message_and_chat_id=[(message, x.chat_id) for x in get_demand_users()],
        workflow=Workflow.DEMAND
    )


def notify_supply_for_booked(*, supply_user: User, message_id: str, demand_user: User):
    reply = build_supply_side_booked_message(
        demand_user=demand_user, supply_user=supply_user, message_id=message_id
    )

    send_messages(
        tg_chat_id=int(supply_user.chat_id),
        replies=[reply],
        workflow=Workflow.SUPPLY,
    )


def notify_demand_for_cancel(*, supply_user: User, message_id: str, message: str):
    demand_user = get_message_demanded_user(supply_user=supply_user, message_id=message_id)
    if demand_user is None:
        raise ValueError('Demand user is not defined.')

    food_description = build_demand_side_full_message_text_by_id(
        supply_user=supply_user, message_id=message_id
    )
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


def notify_demand_for_approved(*, supply_user: User, message_id: str):
    demand_user = get_message_demanded_user(supply_user=supply_user, message_id=message_id)
    if demand_user is None:
        raise ValueError('Demand user is not defined.')

    send_messages(
        tg_chat_id=int(demand_user.chat_id),
        replies=[
            build_demand_side_message_by_id(
                supply_user, message_id, intro=_('Your request was approved')
            )
        ],
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
            except Unauthorized:
                logger.warning(
                    '%s is blocked for the bot. '
                    'TODO: set is_active=False for the user with this chat_id.',
                    tg_chat_id
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
