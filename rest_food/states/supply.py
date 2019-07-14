from rest_food.states.base import State
from rest_food.entities import Reply, SupplyState
from rest_food.db import (
    extend_supply_message,
    create_supply_message,
    cancel_supply_message,
)
from rest_food.communication import publish_supply_event
from .utils import build_active_food_message



class DefaultState(State):
    def handle(self, text: str, data: str):
        return Reply(next_state=SupplyState.READY_TO_POST)


class ReadyToPostState(State):
    intro = Reply(text='Enter food you can share and click "send"')

    def handle(self, text: str, data: str):
        create_supply_message(self.db_user, text, provider=self.provider)
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
            build_active_food_message(self.db_user)
        )
        return reply


    def handle(self, text: str, data: str):
        if data == 'send':
            publish_supply_event(self.db_user)
            return Reply(
                text="Information is sent. "
                     "I'll notify you when there is someone to take this food.",
                next_state=SupplyState.READY_TO_POST,
            )

        if data == 'cancel':
            cancel_supply_message(self.db_user, provider=self.provider)
            return Reply(
                text='Product list is cleared.',
                next_state=SupplyState.READY_TO_POST,
            )

        extend_supply_message(self.db_user, text)
