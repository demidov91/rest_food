from rest_food.entities import User
from rest_food.db import get_supply_editing_message


def build_share_food_message(user: User):
    if not user.editing_message_id:
        raise ValueError("Active message wasn't defined.")

    message = get_supply_editing_message(user)

    return '\n'.join('* ' + line for line in message)
