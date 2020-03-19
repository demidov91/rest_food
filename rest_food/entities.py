import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from decimal import Decimal

from bson import ObjectId
from telegram.user import User as TgUser

from rest_food.translation import translate_lazy as _


DT_FORMAT = '%Y%m%d%H%M%S'
""" Message.dt_published stored datetime as string rather than mongo time. 
"""


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
    # True if the user has shared their username
    DISPLAY_USERNAME = 'display_username'
    # Bot language for this user.
    LANGUAGE = 'language'
    # True for approved coordinates (rather than proposed by system)
    IS_APPROVED_COORDINATES = 'is_approved_coordinates'
    # If the user has explicitly approved specified `LANGUAGE` (rather than set by messeger client language)
    IS_APPROVED_LANGUAGE = 'is_approved_language'
    # demand-side-chosen social status
    SOCIAL_STATUS = 'social_status'
    # True for supply users who are allowed to post messages. Actually it makes sense to move it into the User level...
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
    APPROVE_SUPPLIER = 'approve_supplier'
    DECLINE_SUPPLIER = 'decline_supplier'


@dataclass
class Command:
    name: str
    arguments: List[str]


@dataclass
class User:
    _id: Optional[ObjectId]=None
    """ db level id.
    """

    user_id: Optional[Union[str, int]]=None
    """ External provider id of the user.
    """

    chat_id: Optional[Union[str, int]]=None
    """ External provider defined user-to-bot chat id.
    """

    state: Optional[str] = None
    """ Current bot state for this user.
    """

    info: Optional[Dict] = None
    """ User defined information.
    """

    context: Optional[Dict] = None
    """ Any key-value information to make bot interaction stateful. 
    """

    editing_message_id: Optional[str]=None
    """ Id of the message which is edited at the moment.
    """

    tg_user: Optional[TgUser]=None
    """ TgUser object which can be assigned for convenience. It's not stored in db.
    """

    provider: Optional[Provider]=None
    """ Provider, like telegram or viber.
    """

    workflow: Optional[Workflow]=None
    """ Is it a supply or demand bot user. 
    """

    is_active: Optional[bool]=None
    """ Messages won't be sent for users with this field set to False.
    """

    is_admin: Optional[bool]=False
    """ Users with extended permissions. Like supply users approval. 
    """

    created_at: Optional[datetime.datetime]=None
    """ Moment when user was first created.
    """

    inactive_from: Optional[datetime.datetime]=None
    """ Moment when user was marked as inactive (it could happen much later then they really blocked the bot).
    """

    active_from: Optional[datetime.datetime]=None
    """ Moment when user with undefined or inactive state sent a message, so that their `is_active` field became True.
    """


    @property
    def id(self) -> Optional[ObjectId]:
        return self._id

    def approved_coordinates(self):
        return (
            self.info.get(UserInfoField.IS_APPROVED_COORDINATES.value) and
            self.info.get(UserInfoField.COORDINATES.value)
        )

    def is_approved_supply_is_set(self):
        return UserInfoField.IS_APPROVED_SUPPLY.value in self.info

    @classmethod
    def from_dict(cls, record: dict):
        record['state'] = record.pop('bot_state', None)
        record['workflow'] = Workflow(record.get('workflow'))
        record['provider'] = Provider(record.get('provider'))
        return cls(**record)


@dataclass
class Message:
    message_id: ObjectId
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
    text: Optional[str] = None
    buttons: Optional[List[List[Dict]]] = None
    coordinates: Optional[Tuple[Decimal, Decimal]] = None
    next_state: Optional[Union[DemandState, SupplyState]] = None
    is_text_buttons: bool = False
