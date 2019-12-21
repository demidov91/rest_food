from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from decimal import Decimal

from telegram.user import User as TgUser

from rest_food.translation import translate_lazy as _


class SupplyState(Enum):
    READY_TO_POST = 'ready_to_post'
    POSTING = 'posting'
    SET_TIME = 'set_time'
    VIEW_INFO = 'view_info'
    EDIT_NAME = 'edit_name'
    EDIT_ADDRESS = 'edit_address'
    EDIT_COORDINATES = 'edit-coordinates'
    EDIT_PHONE = 'edit_phone'
    FORCE_NAME = 'force_name'
    FORCE_ADDRESS = 'force_address'
    FORCE_COORDINATES = 'force_coordinates'
    FORCE_PHONE = 'force_phone'


class DemandState(Enum):
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'
    EDIT_SOCIAL_STATUS = 'edit_social_status'


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
    COORDINATES = 'coordinates'
    PHONE = 'phone'
    DISPLAY_USERNAME = 'display_username'
    IS_APPROVED_COORDINATES = 'is_approved_coordinates'
    SOCIAL_STATUS = 'social_status'


class SocialStatus(Enum):
    BIG_FAMILY = 'big_family'
    DISABILITY = 'disability'
    HOMELESS = 'homeless'
    HARD_TIMES = 'hard_times'
    OTHER = 'other'


def translate_social_status_string(ss_string: Optional[str]) -> str:
    if not ss_string:
        return _('not set')

    try:
        ss = SocialStatus(ss_string)
    except ValueError:
        return _('unknown')

    return soc_status_translation.get(ss, _('unknown'))


soc_status_translation = {
    SocialStatus.BIG_FAMILY: _('big family'),
    SocialStatus.DISABILITY: _('disability'),
    SocialStatus.HOMELESS: _('homeless'),
    SocialStatus.HARD_TIMES: _('hard times'),
    SocialStatus.OTHER: _('other'),
}


class DemandCommandName(Enum):
    TAKE = 'take'
    INFO = 'info'
    DISABLE_USERNAME = 'disable-username'
    ENABLE_USERNAME = 'enable-username'
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'
    EDIT_SOCIAL_STATUS = 'edit_ss'
    SET_SOCIAL_STATUS = 'set_ss'
    FINISH_TAKE = 'f_take'


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
    context: Optional[Dict] = None
    editing_message_id: Optional[str]=None
    tg_user: Optional[TgUser]=None
    provider: Optional[Provider]=None
    workflow: Optional[Workflow]=None

    def approved_coordinates(self):
        return (
            self.info.get(UserInfoField.IS_APPROVED_COORDINATES.value) and
            self.info.get(UserInfoField.COORDINATES.value)
        )


@dataclass
class Message:
    products: List[str]
    take_time: Optional[str]
    demand_user_id: Optional[Union[str, int]]


@dataclass
class Reply:
    text: Optional[str]=None
    buttons: Optional[List[List[Dict]]]=None
    coordinates: Optional[Tuple[Decimal, Decimal]]=None
    next_state: Optional[Union[DemandState, SupplyState]]=None


