import datetime
import logging
import re
import time
from typing import Optional

from rest_food.entities import (
    Command,
    DemandCommandName,
    DT_FORMAT,
    User,
)
from rest_food.exceptions import ValidationError

from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


def to_local_time(system_time: datetime.datetime):
    """
    No pytz implementation of utc to utc+3 convertion.
    """
    utc_offset = -time.timezone
    target_offset = datetime.timedelta(hours=3) - datetime.timedelta(seconds=utc_offset)
    return system_time + target_offset


def db_time_to_user(db_time: Optional[str], fmt: str) -> str:
    if not db_time:
        return '~~~'

    return to_local_time(datetime.datetime.strptime(db_time, DT_FORMAT)).strftime(fmt)


def validate_phone_number(text):
    if len(text) > 100:
        raise ValidationError(_('Please, provide only pone number.'))

    number_of_digits = len(re.findall(r'\d', text))
    if number_of_digits < 7:
        raise ValidationError(_('This is not a valid phone number.'))


def get_next_command(user: User) -> Command:
    logger.info('User context: %s', user.context)

    return Command(
        name=user.context['next_command'],
        arguments=user.context['arguments'],
    )


def build_demand_command_button(text: str, command: Command):
    return {
        'text': text,
        'data': DemandCommandName(command.name).build(*command.arguments),
    }


def get_demand_back_button(user: User, text: str=_('Back')):
    return build_demand_command_button(text, get_next_command(user))
