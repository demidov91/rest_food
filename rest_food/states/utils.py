from rest_food.entities import User
from rest_food.db import get_supply_editing_message, get_supply_message


def _message_to_text(message):
    return '\n'.join('* ' + line for line in message)


def build_active_food_message(user: User):
    if not user.editing_message_id:
        raise ValueError("Active message wasn't defined.")

    message = get_supply_editing_message(user)

    return _message_to_text(message)


def build_food_message_by_id(*, user, message_id):
    return _message_to_text(get_supply_message(user=user, message_id=message_id))
