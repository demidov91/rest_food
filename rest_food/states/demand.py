import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from rest_food.communication import notify_supply_for_booked
from rest_food.db import (
    get_user,
    mark_message_as_booked,
    get_supply_message_record,
    set_info,
    set_next_command,
)
from rest_food.entities import (
    User,
    Reply,
    Provider,
    Workflow,
    UserInfoField,
    DemandCommandName,
    Command,
)
from rest_food.states.base import State


logger = logging.getLogger(__name__)


def parse_data(data) -> Command:
    parts = data.split('|')

    logger.info(parts)

    return Command(command=DemandCommandName(parts[0]), arguments=parts[1:])


def handle_demand_data(user: User, data: str):
    return _handle(user, parse_data(data))


def _get_next_command(user: User) -> Command:
    return Command(
        command=DemandCommandName(user.context['next_command']),
        arguments=user.context['arguments'],
    )

def _handle(user: User, command: Command):
    return COMMAND_HANDLERS[command.command](user, *command.arguments)


def handle_demand_text(user: User, text: str):
    if text == '/start':
        return



    return Reply(text='Sorry, dialog and feedback are not implemented yet.')


def _handle_take(user: User, provider_str: str, supply_user_db_id: str, message_id: str):
    set_next_command(
        user,
        Command(
            command=DemandCommandName.TAKE,
            arguments=[provider_str, supply_user_db_id, message_id],
        )
    )

    buttons = _get_review_buttons(user)
    buttons.append([{
        'text': 'ok',
        'data': f'{DemandCommandName.FINISH_TAKE.value}|'
                f'{provider_str}|{supply_user_db_id}|{message_id}',
    }, {
        'text': 'cancel',
        'data': f'{DemandCommandName.CANCEL_TAKE.value}',
    }])

    return Reply(
        text='Please, confirm/edit your contact information to proceed.',
        buttons=buttons,
    )


def _get_review_buttons(user: User):
    buttons = [{
        'text': f'Name: {user.info["name"]}',
        'data': f'{DemandCommandName.EDIT_NAME}',
    }]

    if user.info['username']:
        if user.info['display_username']:
            buttons.append({
                'text': f'Connect via {user.provider.value}: ✅',
                'data': f'{DemandCommandName.DISABLE_USERNAME.value}',
            })
        else:
            buttons.append({
                'text': f'Connect via {user.provider.value}: ❌',
                'data': DemandCommandName.ENABLE_USERNAME.value,
            })

    buttons.append({
        'text': 'Phone: %s' % (user.info.get(UserInfoField.PHONE.value) or 'not set'),
        'data': f'{DemandCommandName.EDIT_PHONE.value}',

    })

    return [[x] for x in buttons]



def _handle_finish_take(user: User, provider_str: str, supply_user_db_id: str, message_id: str):
    supply_user = get_user(
        supply_user_db_id,
        provider=Provider(provider_str),
        workflow=Workflow.SUPPLY
    )

    is_successfully_booked = mark_message_as_booked(
        demand_user=user, supply_user=supply_user, message_id=message_id
    )

    if not is_successfully_booked:
        return Reply(text='Someone has already taken it.')

    notify_supply_for_booked(
        supply_user=supply_user,
        message_id=message_id,
        demand_user=user
    )

    message = f"{supply_user.info['name']} is notified that you'll take it.\n" \
              f"Address: {supply_user.info['address']}\n"

    return Reply(text=message)


def _handle_info(user: User, provider_str: str, supply_user_db_id: str, message_id: str):
    supply_user = get_user(
        supply_user_db_id,
        provider=Provider(provider_str),
        workflow=Workflow.SUPPLY
    )

    if supply_user is None:
        return Reply('Information was not found.')

    info = f"Restaurant name: {supply_user.info['name']}\n" \
           f"Address: {supply_user.info['address']}"


    db_message = get_supply_message_record(user=supply_user, message_id=message_id)

    if db_message.demand_user_id is not None:
        return Reply(text=f"SOMEONE HAS ALREADY TAKEN IT! (maybe you)\n\n{info}")


    return Reply(
        text=info,
        buttons=[[
            {
                'text': 'Take it',
                'data': f'{DemandCommandName.TAKE.value}|'
                        f'{supply_user.provider.value}|'
                        f'{supply_user.user_id}|'
                        f'{message_id}',
            },
        ]]
    )


def _handle_enable_username(user: User):
    set_info(user, UserInfoField.DISPLAY_USERNAME, True)
    command = _get_next_command(user)
    return _handle(user, command)


def _handle_disable_username(user: User):
    set_info(user, UserInfoField.DISPLAY_USERNAME, False)
    command = _get_next_command(user)
    return _handle(user, command)


COMMAND_HANDLERS = {
    DemandCommandName.TAKE: _handle_take,
    DemandCommandName.INFO: _handle_info,
    DemandCommandName.ENABLE_USERNAME: _handle_enable_username,
    DemandCommandName.DISABLE_USERNAME: _handle_disable_username,
    DemandCommandName.FINISH_TAKE: _handle_finish_take,
}


class BaseSetInfoState(State):
    _intro_text = None  # type: str
    _info_field = None  # type: UserInfoField

    def get_intro(self):
        next_command = _get_next_command(self.db_user)

        return Reply(
            text=self._intro_text,
            buttons=[[{
                'text': 'Cancel',
                'data': '{}|{}'.format(
                    next_command.command.value,
                    '|'.join(next_command.arguments)
                ),
            }]],
        )

    def handle(self, text: str, data: Optional[str]=None):
        set_info(self.db_user, self._info_field, text)
        return _handle(self.db_user, _get_next_command(self.db_user))


class SetNameState(BaseSetInfoState):
    _intro_text = 'Enter your name:'
    _info_field = UserInfoField.NAME


class SetPhoneState(BaseSetInfoState):
    _intro_text = 'Enter your phone number:'
    _info_field = UserInfoField.PHONE


class DefaultState(State):
    pass

