from telegram import Update

from rest_food.db import get_or_create_user
from rest_food.entities import Workflow, Provider
from rest_food.state_machine import (
    get_supply_state,
    set_supply_state,
)
from rest_food.communication import send_messages, get_bot
from rest_food.states.demand import handle_demand_data, handle_demand_text


def tg_supply(data):
    update = Update.de_json(data, None)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    tg_user = update.effective_user

    state = get_supply_state(tg_user_id=user_id, tg_user=tg_user, tg_chat_id=chat_id)
    reply = state.handle(
        update.message and update.message.text,
        update.callback_query and update.callback_query.data,
    )
    if reply is not None and reply.next_state is not None:
        next_state = set_supply_state(state.db_user, reply.next_state)
    else:
        next_state = state

    send_messages(
        tg_chat_id=chat_id,
        replies=[reply, next_state.get_intro()],
        workflow=Workflow.SUPPLY
    )


def tg_demand(data):
    update = Update.de_json(data, None)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    user = get_or_create_user(
        user_id=user_id,
        chat_id=chat_id,
        provider=Provider.TG,
        workflow=Workflow.DEMAND
    )

    if update.callback_query is not None:
        reply = handle_demand_data(user=user, data=update.callback_query.data)
    else:
        reply = handle_demand_text(user=user, text=update.message.text)

    if reply is not None:
        send_messages(
            tg_chat_id=chat_id,
            replies=[reply],
            workflow=Workflow.DEMAND
        )


def set_tg_webhook(url: str, *, workflow: Workflow):
    get_bot(workflow).set_webhook(url)
