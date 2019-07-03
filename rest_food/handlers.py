from telegram.update import Update

from rest_food.state_machine import get_supply_state, set_supply_state
from rest_food.utils import send_messages


def tg_supply(data):
    update = Update.de_json(data, None)
    state = get_supply_state(update.message.from_user)
    reply = state.handle(update.message)
    if reply.next_state is not None:
        next_state = set_supply_state(reply.next_state)
    else:
        next_state = state

    send_messages(update.message.from_user, [reply, next_state.intro])


def tg_demand(data):
    pass

