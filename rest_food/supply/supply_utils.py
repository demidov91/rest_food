import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from rest_food.common.constants import MESSAGE_UI_DT_TIME_FORMAT, DT_DB_FORMAT


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