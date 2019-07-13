import logging
from typing import Iterable

from telegram import Bot

from rest_food.entities import Reply
from rest_food.settings import TELEGRAM_TOKEN


logger = logging.getLogger(__name__)


def get_bot():
    return Bot(TELEGRAM_TOKEN)


def notify_admin(user):
    pass


def publish_supply_event(db_id: str):
    logger.info(f'Mock sending an event from {db_id}')


def send_messages(tg_chat_id: int, replies:Iterable[Reply]):
    bot = get_bot()

    for reply in filter(lambda x: x is not None, replies):
        bot.send_message(
            tg_chat_id,
            reply.text,
            reply_markup=_build_tg_keyboard(reply.buttons)
        )


def _build_tg_keyboard(keyboard):
    inline_keyboard = [
        [
            _build_tg_keyboard_cell(cell) for cell in row
        ] for row in keyboard
    ]

    return {
        'inline_keyboard': inline_keyboard,
    }


def _build_tg_keyboard_cell(cell):
    if isinstance(cell, str):
        return {
            'text': cell,
            'callback_data': cell,
        }

    return {
        'text': cell['text'],
        'callback_data': cell['data'],
    }
