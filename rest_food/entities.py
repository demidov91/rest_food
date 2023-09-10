import datetime
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from decimal import Decimal

from bson import ObjectId
from telegram.user import User as TgUser

from rest_food.enums import DemandState, SupplyState, Provider, Workflow, SocialStatus, UserInfoField, MessageState
from rest_food.translation import translate_lazy as _
from rest_food import settings


soc_status_translation = {
    SocialStatus.BIG_FAMILY: _('big family'),
    SocialStatus.DISABILITY: _('disability'),
    SocialStatus.HOMELESS: _('homeless'),
    SocialStatus.HARD_TIMES: _('hard times'),
    SocialStatus.EMIGRANT: _('emigrant'),
    SocialStatus.OTHER: _('other'),
}


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
            self.get_info_field(UserInfoField.IS_APPROVED_COORDINATES) and
            self.get_info_field(UserInfoField.COORDINATES)
        )

    def is_approved_supply_is_set(self):
        return UserInfoField.IS_APPROVED_SUPPLY.value in self.info

    def get_info_field(self, field: UserInfoField):
        return self.info.get(field.value)

    def get_translated_social_status(self):
        ss_string = self.get_info_field(UserInfoField.SOCIAL_STATUS)
        if not ss_string:
            return None

        try:
            ss = SocialStatus(ss_string)
        except ValueError:
            return None

        return soc_status_translation.get(ss)

    @classmethod
    def from_dict(cls, record: dict):
        record['state'] = record.pop('bot_state', None)
        record['workflow'] = Workflow(record.get('workflow'))
        record['provider'] = Provider(record.get('provider'))
        record['is_admin'] = (
            record.get('is_admin')
            or (record.get('info', {}).get(UserInfoField.USERNAME.value) in settings.ADMIN_USERNAMES)
        )
        return cls(**record)


@dataclass
class Message:
    message_id: ObjectId
    owner_id: str
    products: List[str]
    take_time: Optional[str] = None
    demand_user_id: Optional[Union[str, int]] = None
    dt_published: Optional[str] = None
    state: Optional[MessageState] = None

    @classmethod
    def from_db(cls, record: dict):
        record['message_id'] = record.pop('_id')
        record['state'] = record.get('state') and MessageState(record['state'])
        return Message(**record)


@dataclass
class Reply:
    text: Optional[str] = None
    buttons: Optional[List[List[Dict]]] = None
    coordinates: Optional[Tuple[Decimal, Decimal]] = None
    next_state: Optional[Union[DemandState, SupplyState]] = None
    is_text_buttons: bool = False
