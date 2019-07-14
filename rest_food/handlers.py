from telegram import Bot, Update

from rest_food.settings import TELEGRAM_TOKEN
from rest_food.state_machine import get_supply_state, set_supply_state
from rest_food.communication import send_messages


def tg_supply(data):
    update = Update.de_json(data, None)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    tg_user = update.effective_user

    state = get_supply_state(user_id, tg_user=tg_user)
    reply = state.handle(
        update.message and update.message.text,
        update.callback_query and update.callback_query.data,
    )
    if reply is not None and reply.next_state is not None:
        next_state = set_supply_state(state.db_user, reply.next_state)
    else:
        next_state = state

    send_messages(tg_chat_id=chat_id, replies=[reply, next_state.get_intro()])


def tg_demand(data):
    pass


def set_tg_webhook(url):
    bot = Bot(TELEGRAM_TOKEN)
    bot.set_webhook(url)
