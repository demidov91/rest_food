import logging
from dataclasses import dataclass
from typing import List

from rest_food.communication import notify_supply_for_booked
from rest_food.db import get_user, mark_message_as_booked
from rest_food.entities import User, Reply, Provider, Workflow


logger = logging.getLogger(__name__)


@dataclass
class Command:
    command: str
    arguments: List[str]


def parse_data(data) -> Command:
    parts = data.split('|')
    return Command(command=parts[0], arguments=parts[1:])


def handle_demand_data(user, data: str):
    command = parse_data(data)
    return COMMAND_HANDLERS[command.command](user, *command.arguments)


def handle_demand_text(user: User, text: str):
    if text == '/start':
        return

    return Reply(text='Sorry, dialog and feedback are not implemented yet.')


def _handle_take(user: User, supply_user_db_id: str, message_id: str):
    supply_user = get_user(supply_user_db_id, provider=Provider.TG, workflow=Workflow.SUPPLY)

    is_successfully_booked = mark_message_as_booked(
        demand_user=user, supply_user_id=supply_user_db_id, message_id=message_id
    )

    if not is_successfully_booked:
        return Reply(text='Someone has already taken it.')

    notify_supply_for_booked(
        supply_user=supply_user,
        message_id=message_id,
        demand_user=user
    )

    message = f"{supply_user.info['name']} is notified that you'll take it.\n" \
              f"Address: {supply_user.info['address']}\n" \
              f"Time: {supply_user.info['time_to_visit']}"

    return Reply(text=message)


def _handle_info(user: User, supply_user_db_id: str, message_id: str):
    supply_user = get_user(supply_user_db_id, provider=Provider.TG, workflow=Workflow.SUPPLY)

    message = f"Address: {supply_user.info['address']}\n" \
              f"Time: {supply_user.info['time_to_visit']}"

    return Reply(
        text=message,
        buttons=[[
            {'text': 'Take it', 'data': f'take|{supply_user_db_id}|{message_id}'},
        ]]
    )


COMMAND_HANDLERS = {
    'take': _handle_take,
    'info': _handle_info,
}
