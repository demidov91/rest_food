"""
Module with generic wrappers for sending bot messages. They are usually sent via queue.
"""

import logging
import random

from rest_food.db import (
    get_message_demanded_user, get_admin_users, set_info,
    get_demand_users)
from rest_food.entities import Reply, User, Workflow, UserInfoField, SupplyCommand
from rest_food.message_queue import get_mass_queue, get_single_queue
from rest_food.settings import FEEDBACK_TG_BOT
from rest_food.states.demand_reply import build_demand_side_short_message, \
    build_demand_side_message_by_id
from rest_food.states.supply_reply import (
    build_supply_side_booked_message, build_new_supplier_notification,
)
from rest_food.states.formatters import build_demand_side_full_message_text_by_id
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


def publish_supply_event(supply_user: User):
    message = build_demand_side_short_message(supply_user, supply_user.editing_message_id)
    users = get_demand_users()
    random.shuffle(users)
    get_mass_queue().push_super_batch(
        message_and_chat_id=[(message, x.chat_id) for x in users],
        workflow=Workflow.DEMAND
    )


def notify_supply_for_booked(*, supply_user: User, message_id: str, demand_user: User):
    reply = build_supply_side_booked_message(
        demand_user=demand_user, supply_user=supply_user, message_id=message_id
    )

    queue_messages(
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

    queue_messages(
        tg_chat_id=int(demand_user.chat_id),
        replies=[Reply(text=text_to_send)],
        workflow=Workflow.DEMAND,
    )


def notify_demand_for_approved(*, supply_user: User, message_id: str):
    demand_user = get_message_demanded_user(supply_user=supply_user, message_id=message_id)
    if demand_user is None:
        raise ValueError('Demand user is not defined.')

    queue_messages(
        tg_chat_id=int(demand_user.chat_id),
        replies=[
            build_demand_side_message_by_id(
                supply_user, message_id, intro=_('Your request was approved')
            )
        ],
        workflow=Workflow.DEMAND,
    )


def notify_admin_about_new_supply_user_if_necessary(supply_user: User):
    if supply_user.is_approved_supply_is_set():
        logger.debug('Admins are already notified.')
        return

    admin_users = get_admin_users()
    message = build_new_supplier_notification(supply_user)
    if not admin_users:
        logger.error("There are no admin users in db.")
        return 

    for admin_user in admin_users:
        if admin_user.workflow == Workflow.DEMAND:
            logger.warning(
                "Notification won't be sent user %s as admin should be supplier.",
                admin_user.id
            )
        else:
            queue_messages(
                tg_chat_id=admin_user.chat_id,
                replies=[message],
                workflow=Workflow.SUPPLY
            )

    set_info(supply_user, UserInfoField.IS_APPROVED_SUPPLY, None)


def notify_supplier_is_approved(user: User):
    queue_messages(
        tg_chat_id=user.chat_id,
        workflow=Workflow.SUPPLY,
        replies=[
            Reply(
                text=_('Your account is approved!'),
                buttons=[[{
                    'data': f'c|{SupplyCommand.BACK_TO_POSTING}',
                    'text': _('OK ✅'),
                }]]
            )
        ],
    )


def notify_supplier_is_declined(user: User):
    queue_messages(
        tg_chat_id=user.chat_id,
        workflow=Workflow.SUPPLY,
        replies=[
            Reply(
                text=(
                    _('Your account was declined. Please, contact %s for any clarifications.') %
                    FEEDBACK_TG_BOT
                )
            )
        ],
    )


def queue_messages(**kwargs):
    """
    Put messages into a single-message-queue
    """
    get_single_queue().put(**kwargs)
