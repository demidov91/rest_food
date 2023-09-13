import pytest
from zoneinfo import ZoneInfo

from rest_food.supply.supply_utils import db_time_to_user


@pytest.mark.parametrize('db_time, timezone, expected', [
    ('', ZoneInfo('Europe/Minsk'), '~~~'),
    ('2018-07-15 12:00:22', ZoneInfo('Europe/Minsk'), '15-07 15:00'),
    ('2018-07-15 12:00:22', ZoneInfo('Europe/Vilnius'), '15-07 15:00'),
    ('2018-11-15 12:00:22', ZoneInfo('Europe/Minsk'), '15-11 15:00'),
    ('2018-11-15 12:00:22', ZoneInfo('Europe/Vilnius'), '15-11 14:00'),
    ('2018-11-15 12:00:22', None, '15-11 12:00 utc'),
])
def test_db_time_to_user(db_time, timezone, expected):
    assert db_time_to_user(db_time, timezone) == expected
