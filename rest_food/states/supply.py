from telegram import Message

from rest_food.states.base import State
from rest_food.common_bot import Reply
from rest_food.db import (
    get_user,
    extend_supply_message,
    publish_supply,
)
from rest_food.utils import notify_admin
from rest_food.state_enum import SupplyState

class DefaultState(State):
    def handle(self, message: Message):
        db_supply = get_supply(tg_user_id=message.from_user.id)
        if db_supply is None:
            notify_admin(message.from_user)

            return Reply(
                text='Admin is notified. Try later.',
                buttons=[['Try again']]
            )

        return Reply(next_state=SupplyState.POSTING)


class ReadyToPostState(State):
    intro = Reply(text='Enter food you can share and click "send"')

    def handle(self, message: Message):
        extend_supply_message(message.text)
        return Reply(next_state=SupplyState.POSTING)


class PostingState(State):
    intro = Reply(buttons=[['send', 'cancel']])

    def handle(self, message: Message):
        if message.text == 'send':
            publish_supply(self.db_user['id'])
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

        extend_supply_message(message.text)
