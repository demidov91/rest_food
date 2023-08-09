from contextlib import contextmanager

from rest_food.entities import UserInfoField
from rest_food.translation import switch_language


@contextmanager
def user_language(user):
    with switch_language(user.get_info_field(UserInfoField.LANGUAGE)):
        yield
