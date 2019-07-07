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
    user_id: Union[str, int]
    provider: Provider
    workflow: Workflow
    id: Optional[str] = None
    state: Optional[str] = None
    info: Optional[Dict] = None


@dataclass
class Reply:
    text: Optional[str]=None
    buttons: Optional[List[List[Dict]]]=None
    next_state: Optional[Union[DemandState, SupplyState]]=None


