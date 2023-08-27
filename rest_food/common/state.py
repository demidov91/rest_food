from copy import deepcopy
from typing import Optional, Tuple
from decimal import Decimal

from rest_food.entities import Reply, User
from rest_food.enums import Provider


class State:
    intro = None    # type: Reply

    def __init__(self, db_user: User, provider=Provider.TG):
        self.db_user = db_user
        self.provider = provider

    def get_intro(self) -> Reply:
        return deepcopy(self.intro)

    def handle(
            self,
            text: str,
            data: Optional[str],
            coordinates: Optional[Tuple[Decimal, Decimal]]
    ) -> Reply:
        pass
