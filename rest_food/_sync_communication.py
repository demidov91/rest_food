"""
You're expected to send messages via queues (async): *message_queue*.
This is a module with underlying synchronous implementation.
"""
import logging
import time
from typing import Iterable

from telegram import Bot, Message as TgMessage
from telegram.error import Unauthorized, BadRequest

from rest_food.db import set_inactive
from rest_food.entities import Workflow, Message, Reply, Provider
from rest_food.settings import TEST_TG_CHAT_ID, TELEGRAM_TOKEN_DEMAND, TELEGRAM_TOKEN_SUPPLY, STAGE

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
            return self._bot.send_location(chat_id, *args, **kwargs)
        else:
            self._sleep()

    def edit_message_text(self, text, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            return self._bot.edit_message_text(text, chat_id, *args, **kwargs)
        else:
            self._sleep()

    def send_message(self, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            return self._bot.send_message(chat_id, *args, **kwargs)
        else:
            self._sleep()

    def delete_message(self, chat_id, *args, **kwargs):
        if chat_id in TEST_TG_CHAT_ID:
            return self._bot.delete_message(chat_id, *args, **kwargs)
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


def send_messages(
    *,
    tg_chat_id: int,
    original_message: TgMessage = None,
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
            logger.info('Sending location to %s', tg_chat_id)

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

            logging.info('Sending a text message to %s', tg_chat_id)

            try:
                send_result = method(
                    chat_id=tg_chat_id,
                    text=reply.text,
                    reply_markup=markup,
                    message_id=original_message and original_message.message_id
                )
            except Unauthorized:
                logger.warning(
                    '%s is blocked for the bot. ',
                    tg_chat_id
                )
                set_inactive(chat_id=tg_chat_id, provider=Provider.TG, workflow=workflow)

            except BadRequest as e:
                if 'the same' in e.message:
                    pass
                elif 'Chat not found' in e.message:
                    logger.warning('Tg chat %s not found', tg_chat_id)
                    set_inactive(chat_id=tg_chat_id, provider=Provider.TG, workflow=workflow)
                else:
                    logger.warning('Failed to send to tg_chat_id=%s', tg_chat_id)
                    raise e

            else:
                logger.info(
                    'Text message was successfully sent to %s. Send result is %s',
                    tg_chat_id, send_result
                )

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
