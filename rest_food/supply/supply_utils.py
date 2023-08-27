import datetime
import time
from typing import Optional

from rest_food.entities import DT_FORMAT


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