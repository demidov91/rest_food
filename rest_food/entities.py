from enum import Enum
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from telegram.user import User as TgUser


class SupplyState(Enum):
    READY_TO_POST = 'ready_to_post'
    POSTING = 'posting'
    SET_TIME = 'set_time'
    VIEW_INFO = 'view_info'
    EDIT_NAME = 'edit_name'
    EDIT_ADDRESS = 'edit_address'
    EDIT_PHONE = 'edit_phone'
    FORCE_NAME = 'force_name'
    FORCE_ADDRESS = 'force_address'
    FORCE_PHONE = 'force_phone'


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
    cluster: Optional[str]=None
    user_id: Optional[Union[str, int]]=None
    chat_id: Optional[Union[str, int]]=None
    state: Optional[str] = None
    info: Optional[Dict] = None
    editing_message_id: Optional[str]=None
    tg_user: Optional[TgUser]=None
    provider: Optional[Provider]=None
    workflow: Optional[Workflow]=None


@dataclass
class Reply:
    text: Optional[str]=None
    buttons: Optional[List[List[Dict]]]=None
    next_state: Optional[Union[DemandState, SupplyState]]=None


