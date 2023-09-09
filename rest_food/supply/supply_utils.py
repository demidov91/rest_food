import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from rest_food.entities import DT_FORMAT


def to_local_time(system_time: datetime.datetime):
    return system_time.replace(tzinfo=datetime.timezone.utc).astimezone(ZoneInfo('Europe/Minsk'))


def db_time_to_user(db_time: Optional[str], fmt: str) -> str:
    if not db_time:
        return '~~~'

    return to_local_time(datetime.datetime.strptime(db_time, DT_FORMAT)).strftime(fmt)