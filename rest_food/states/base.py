from copy import deepcopy
from typing import Union, Optional

from telegram import Message

from rest_food.entities import SupplyState, DemandState, Reply


class State:
    intro = None    # type: Reply

    def __init__(self, db_user):
        self.db_user = db_user

    def get_intro(self) -> Reply:
        return deepcopy(self.intro)

    def handle(self, text: str, data: Optional[str]) -> Reply:
        pass
