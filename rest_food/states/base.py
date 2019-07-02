from typing import Union

from telegram import Message

from rest_food.state_enum import SupplyState, DemandState
from rest_food.common_bot import Reply


class State:
    intro = None    # type: Reply

    def __init__(self, db_user):
        self.db_user = db_user

    def handle(self, message: Message):
        pass


