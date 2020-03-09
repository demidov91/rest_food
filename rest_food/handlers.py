import logging
from typing import Optional

from telegram import Update

from rest_food.db import get_or_create_user
from rest_food.entities import Workflow, Provider, Reply, SupplyState, UserInfoField
from rest_food.state_machine import (
    get_supply_state,
    set_supply_state,
    get_demand_state,
    set_demand_state,
)
from rest_food._sync_communication import get_bot, build_tg_response
from rest_food.communication import queue_messages
from rest_food.states.demand_command import handle_demand_data
from rest_food.states.supply_state import DefaultState
from rest_food.states.supply_command import handle_supply_command, SupplyCommand
from rest_food.tg_helpers import update_to_text, update_to_coordinates
from rest_food.translation import hack_telegram_json_dumps, translate_lazy as _


logger = logging.getLogger(__name__)


hack_telegram_json_dumps()


def tg_supply(data):
    update = Update.de_json(data, None)

    if not update.effective_user:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    tg_user = update.effective_user
    data = update.callback_query and update.callback_query.data     # type: Optional[str]

    try:
        state = get_supply_state(tg_user_id=user_id, tg_user=tg_user, tg_chat_id=chat_id)
        db_user = state.db_user

        if data and data.startswith('c|'):
            parts = data.split('|')
            reply = handle_supply_command(db_user, parts[1], parts[2:])
            if reply.next_state is None:
                reply.next_state = SupplyState.NO_STATE

        else:
            if update.message and update.message.text == '/start':
                state = set_supply_state(db_user, None)

            reply = state.handle(
                update_to_text(update),
                data,
                update_to_coordinates(update),
            )

        if reply is not None and reply.next_state is not None:
            next_state = set_supply_state(db_user, reply.next_state)
        else:
            next_state = state

        if isinstance(state, DefaultState):
            return build_tg_response(chat_id=chat_id, reply=next_state.get_intro())

        queue_messages(
            tg_chat_id=chat_id,
            original_message=update.callback_query and update.callback_query.message,
            replies=[reply, next_state.get_intro()],
            workflow=Workflow.SUPPLY
        )

        if update.callback_query:
            return {
                'method': 'answerCallbackQuery',
                'callback_query_id': update.callback_query.id,
            }

    except Exception:
        logger.exception('Something went wrong for a supply user.')
        return build_tg_response(
            chat_id=chat_id,
            reply=Reply(
                text=_('Something went wrong. Try something different, please.'),
                buttons=[[{
                    'data': f'c|{SupplyCommand.BACK_TO_POSTING}',
                    'text': _('Start from the beginning'),
                }]]
            )
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
                UserInfoField.NAME.value: tg_user.first_name,
                UserInfoField.USERNAME.value: tg_user.username,
                UserInfoField.LANGUAGE.value: tg_user.language_code,
            },
        )

        if update.callback_query is not None:
            reply = handle_demand_data(user=user, data=update.callback_query.data)
        else:
            if text == '/start':
                set_demand_state(user, None)

            state = get_demand_state(user)
            reply = state.handle(
                update_to_text(update),
                data=None,
                coordinates=update_to_coordinates(update),
            )

        replies = [reply]

        if reply is not None:
            if reply.next_state is not None:
                next_state = set_demand_state(user=user, state=reply.next_state)
                replies.append(next_state.get_intro())

            queue_messages(
                tg_chat_id=chat_id,
                original_message=update.callback_query and update.callback_query.message,
                replies=replies,
                workflow=Workflow.DEMAND
            )

        if update.callback_query:
            return {
                'method': 'answerCallbackQuery',
                'callback_query_id': update.callback_query.id,
            }

    except Exception:
        logger.exception('Something went wrong for a demand user.')
        return build_tg_response(
            chat_id=chat_id,
            reply=Reply(text=_('Something went wrong. Try something different, please.'))
        )


def set_tg_webhook(url: str, *, workflow: Workflow):
    get_bot(workflow).set_webhook(url)
