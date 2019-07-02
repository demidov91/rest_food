from typing import Dict, List, Union
from dataclasses import dataclass

from rest_food.state_enum import SupplyState, DemandState


@dataclass
class Reply:
    text: str
    buttons: List[List[Dict]]
    next_state: Union[DemandState, SupplyState]
