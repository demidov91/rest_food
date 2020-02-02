from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from decimal import Decimal

from telegram.user import User as TgUser

from rest_food.translation import translate_lazy as _


DT_FORMAT = '%Y%m%d%H%M%S'


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
    BOOKING_CANCEL_REASON = 'booking_cancel_reason'
    NO_STATE = 'no_state'


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
    # tg/viber username
    USERNAME = 'username'
    # supply place name
    NAME = 'name'
    # supply address
    ADDRESS = 'address'
    # supply coordinates
    COORDINATES = 'coordinates'
    # contact phone
    PHONE = 'phone'
    # username to display
    DISPLAY_USERNAME = 'display_username'
    # True for approved coordinates (rather then proposed by system)
    IS_APPROVED_COORDINATES = 'is_approved_coordinates'
    # demand-side-chosen social status
    SOCIAL_STATUS = 'social_status'
    # True for supply users who are allowed to post messages
    IS_APPROVED_SUPPLY = 'is_approved_supply'


class SocialStatus(Enum):
    BIG_FAMILY = 'big_family'
    DISABILITY = 'disability'
    HOMELESS = 'homeless'
    HARD_TIMES = 'hard_times'
    OTHER = 'other'


def translate_social_status_string(ss_string: Optional[str]) -> Optional[str]:
    if not ss_string:
        return None

    try:
        ss = SocialStatus(ss_string)
    except ValueError:
        return None

    return soc_status_translation.get(ss)


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
    SHORT_INFO = 'sinf'
    DISABLE_USERNAME = 'disable-username'
    ENABLE_USERNAME = 'enable-username'
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'
    EDIT_SOCIAL_STATUS = 'edit_ss'
    SET_SOCIAL_STATUS = 'set_ss'
    FINISH_TAKE = 'f_take'
    BOOKED = 'bkd'
    MAP_INFO = 'mapi'
    MAP_TAKE = 'mapt'
    MAP_BOOKED = 'mapb'

    def build(self, *args):
        return '|'.join((self.value, ) + args)


class SupplyCommand:
    CANCEL_BOOKING = 'cancel_booking'
    APPROVE_BOOKING = 'approve_booking'
    BACK_TO_POSTING = 'back_to_posting'
    LIST_MESSAGES = 'list_messages'
    SHOW_DEMANDED_MESSAGE = 'sdm'
    SHOW_NON_DEMANDED_MESSAGE = 'show_ndm'


@dataclass
class Command:
    name: str
    arguments: List[str]


@dataclass
class User:
    _id: Optional[str]=None
    user_id: Optional[Union[str, int]]=None
    chat_id: Optional[Union[str, int]]=None
    state: Optional[str] = None
    info: Optional[Dict] = None
    context: Optional[Dict] = None
    editing_message_id: Optional[str]=None
    tg_user: Optional[TgUser]=None
    provider: Optional[Provider]=None
    workflow: Optional[Workflow]=None
    is_active: Optional[bool]=None

    @property
    def id(self) -> Optional[str]:
        return self._id

    def approved_coordinates(self):
        return (
            self.info.get(UserInfoField.IS_APPROVED_COORDINATES.value) and
            self.info.get(UserInfoField.COORDINATES.value)
        )

    @classmethod
    def from_dict(cls, record: dict):
        record['state'] = record.pop('bot_state', None)
        record['workflow'] = Workflow(record.get('workflow'))
        record['provider'] = Provider(record.get('provider'))
        return cls(**record)


@dataclass
class Message:
    message_id: str
    owner_id: str
    products: List[str]
    take_time: Optional[str] = None
    demand_user_id: Optional[Union[str, int]] = None
    dt_published: Optional[str] = None

    @classmethod
    def from_db(cls, record: dict):
        record['message_id'] = record.pop('_id')
        return Message(**record)


@dataclass
class Reply:
    text: Optional[str]=None
    buttons: Optional[List[List[Dict]]]=None
    coordinates: Optional[Tuple[Decimal, Decimal]]=None
    next_state: Optional[Union[DemandState, SupplyState]]=None


