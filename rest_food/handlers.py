import logging
from decimal import Decimal

from telegram import Update

from rest_food.db import get_or_create_user
from rest_food.entities import Workflow, Provider, Reply
from rest_food.state_machine import (
    get_supply_state,
    set_supply_state,
    get_demand_state,
    set_demand_state,
)
from rest_food.communication import send_messages, get_bot, build_tg_response
from rest_food.states.demand import handle_demand_data
from rest_food.states.supply import DefaultState
from rest_food.translation import hack_telegram_json_dumps, translate_lazy as _


logger = logging.getLogger(__name__)


hack_telegram_json_dumps()

def _get_original_message_id(update):
    return (
        update.callback_query and
        update.callback_query.message and
        update.callback_query.message.message_id
    )



def tg_supply(data):
    update = Update.de_json(data, None)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    tg_user = update.effective_user

    try:
        state = get_supply_state(tg_user_id=user_id, tg_user=tg_user, tg_chat_id=chat_id)

        if update.message and update.message.text == '/start':
            state = set_supply_state(state.db_user, None)

        reply = state.handle(
            update.message and update.message.text,
            update.callback_query and update.callback_query.data,
            (
                    update.message and
                    update.message.location and
                    (
                        Decimal(str(update.message.location.latitude)),
                        Decimal(str(update.message.location.longitude))
                    )
            )
        )
        if reply is not None and reply.next_state is not None:
            next_state = set_supply_state(state.db_user, reply.next_state)
        else:
            next_state = state

        if isinstance(state, DefaultState):
            return build_tg_response(chat_id=chat_id, reply=next_state.get_intro())

        original_message_id = _get_original_message_id(update)

        send_messages(
            tg_chat_id=chat_id,
            original_message_id=original_message_id,
            replies=[reply, next_state.get_intro()],
            workflow=Workflow.SUPPLY
        )

    except Exception:
        logger.exception('Something went wrong for a supply user.')
        return build_tg_response(
            chat_id=chat_id,
            reply=Reply(text=_('Something went wrong. Try something different, please.'))
        )


def tg_demand(data):
    update = Update.de_json(data, None)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    tg_user = update.effective_user
    text = update.message and update.message.text

    try:

        user = get_or_create_user(
            user_id=user_id,
            chat_id=chat_id,
            provider=Provider.TG,
            workflow=Workflow.DEMAND,
            info={
                'name': tg_user.first_name,
                'username': tg_user.username,
            },
        )

        if update.callback_query is not None:
            reply = handle_demand_data(user=user, data=update.callback_query.data)
        else:
            if text == '/start':
                set_demand_state(user, None)

            state = get_demand_state(user)
            reply = state.handle(update.message.text, data=None)

        replies = [reply]

        if reply is not None:
            if reply.next_state is not None:
                next_state = set_demand_state(user=user, state=reply.next_state)
                replies.append(next_state.get_intro())

            original_message_id = _get_original_message_id(update)

            send_messages(
                tg_chat_id=chat_id,
                original_message_id=original_message_id,
                replies=replies,
                workflow=Workflow.DEMAND
            )

    except Exception:
        logger.exception('Something went wrong for a demand user.')
        return build_tg_response(
            chat_id=chat_id,
            reply=Reply(text=_('Something went wrong. Try something different, please.'))
        )


def set_tg_webhook(url: str, *, workflow: Workflow):
    get_bot(workflow).set_webhook(url)
