from telegram import Message

from rest_food.states.base import State
from rest_food.entities import Reply, SupplyState
from rest_food.db import (
    get_supply_user,
    extend_supply_message,
    publish_supply,
    create_supply_message,
)
from rest_food.communication import notify_admin, publish_supply_event
from .utils import build_share_food_message



class DefaultState(State):
    def handle(self, message: Message):
        db_supply = get_supply_user(tg_user_id=message.from_user.id)
        if db_supply is None:
            notify_admin(message.from_user)

            return Reply(
                text='Admin is notified. Try later.',
                buttons=[['Try again']]
            )

        return Reply(next_state=SupplyState.READY_TO_POST)


class ReadyToPostState(State):
    intro = Reply(text='Enter food you can share and click "send"')

    def handle(self, message: Message):
        create_supply_message(self.db_user, message.text)
        return Reply(next_state=SupplyState.POSTING)


class PostingState(State):
    intro = Reply(
        buttons=[['send', 'cancel']]
    )

    def get_intro(self):
        reply = super().get_intro()
        reply.text = 'Food you can share:\n' \
                     '{}\n' \
                     'Add more items, SEND or CANCEL'.format(
            build_share_food_message(self.db_user)
        )
        return reply


    def handle(self, message: Message):
        if message.text == 'send':
            publish_supply(self.db_user.db_id)
            return Reply(
                text="Information is sent. "
                     "I'll notify you when there is someone to take this food.",
                next_state=SupplyState.READY_TO_POST,
            )

        if message.text == 'cancel':
            return Reply(
                text='Product list is cleared.',
                next_state=SupplyState.READY_TO_POST,
            )

        extend_supply_message(self.db_user, message.text)
