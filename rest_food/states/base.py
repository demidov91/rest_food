from copy import deepcopy
from typing import Optional

from rest_food.entities import Reply, Provider, User


class State:
    intro = None    # type: Reply

    def __init__(self, db_user: User, provider=Provider.TG):
        self.db_user = db_user
        self.provider = provider

    def get_intro(self) -> Reply:
        return deepcopy(self.intro)

    def handle(self, text: str, data: Optional[str]) -> Reply:
        pass
