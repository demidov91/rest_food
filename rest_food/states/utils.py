from rest_food.entities import User, Message
from rest_food.db import get_supply_editing_message, get_supply_message_record


def _message_to_text(message: Message):
    text_message = '\n'.join(message.products)

    if message.take_time:
        text_message += f'\nTime: {message.take_time}'

    return text_message


def build_active_food_message(user: User):
    if not user.editing_message_id:
        raise ValueError("Active message wasn't defined.")

    message = get_supply_editing_message(user)

    return _message_to_text(message)


def build_food_message_by_id(*, user, message_id):
    return _message_to_text(get_supply_message_record(user=user, message_id=message_id))
