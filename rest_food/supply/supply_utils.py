import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from rest_food.common.constants import MESSAGE_UI_DT_TIME_FORMAT, DT_DB_FORMAT
from rest_food.entities import Message, User
from rest_food.enums import MessageState
from rest_food.user_utilities import get_user_timezone
from rest_food.translation import translate_lazy as _


STATE_TO_MESSAGE = {
    MessageState.PUBLISHED: _('published'),
    MessageState.DEACTIVATED: _('deactivated'),
    MessageState.BOOKED: _('booked'),
    MessageState.APPROVED: _('approved'),
    MessageState.TAKEN: _('taken'),
}


def db_time_to_user(db_time: Optional[str], timezone: Optional[ZoneInfo]) -> str:
    if not db_time:
        return '~~~'

    utc_time = datetime.datetime.strptime(db_time, DT_DB_FORMAT).replace(tzinfo=datetime.timezone.utc)
    if timezone is None:
        timezone = datetime.timezone.utc
        format = MESSAGE_UI_DT_TIME_FORMAT + ' utc'

    else:
        format = MESSAGE_UI_DT_TIME_FORMAT

    local_time = utc_time.astimezone(timezone)
    return local_time.strftime(format)


def get_message_caption(user: User, message: Message):
    timezone = get_user_timezone(user)
    published_display_time = db_time_to_user(message.dt_published, timezone)

    if message.take_time:
        display_time = f'{published_display_time} → {message.take_time}'

    else:
        display_time = published_display_time

    display_state = STATE_TO_MESSAGE[message.state] if message.state is not None else '?'

    return '{} ({})'.format(display_time, display_state)