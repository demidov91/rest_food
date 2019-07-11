from enum import Enum
from typing import Dict, List, Optional, Union
from dataclasses import dataclass


class SupplyState(Enum):
    READY_TO_POST = 'ready_to_post'
    POSTING = 'posting'


class DemandState(Enum):
    pass


class Provider(Enum):
    TG = 'telegram'
    VB = 'viber'


class Workflow(Enum):
    SUPPLY = 'supply'
    DEMAND = 'demand'


@dataclass
class User:
    id: Optional[str] = None
    user_id: Optional[Union[str, int]]=None
    state: Optional[str] = None
    info: Optional[Dict] = None
    editing_message_id: Optional[str]=None


@dataclass
class Reply:
    text: Optional[str]=None
    buttons: Optional[List[List[Dict]]]=None
    next_state: Optional[Union[DemandState, SupplyState]]=None


