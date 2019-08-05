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
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'


class Provider(Enum):
    TG = 'telegram'
    VB = 'viber'


class Workflow(Enum):
    SUPPLY = 'supply'
    DEMAND = 'demand'


class UserInfoField(Enum):
    USERNAME = 'username'
    NAME = 'name'
    ADDRESS = 'address'
    PHONE = 'phone'
    DISPLAY_USERNAME = 'display_username'


class DemandCommandName(Enum):
    TAKE = 'take'
    INFO = 'info'
    DISABLE_USERNAME = 'disable-username'
    ENABLE_USERNAME = 'enable-username'
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'
    FINISH_TAKE = 'finish_take'
    CANCEL_TAKE = 'cancel_take'


@dataclass
class Command:
    command: DemandCommandName
    arguments: List[str]



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
class Message:
    products: List[str]
    take_time: Optional[str]
    demand_user_id: Optional[Union[str, int]]


@dataclass
class Reply:
    text: Optional[str]=None
    buttons: Optional[List[List[Dict]]]=None
    next_state: Optional[Union[DemandState, SupplyState]]=None


