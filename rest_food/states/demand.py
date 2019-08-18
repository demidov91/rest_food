import logging
from typing import Optional

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
    DemandState,
    Command,
)
from rest_food.exceptions import ValidationError
from rest_food.states.base import State
from rest_food.translation import translate_lazy as _
from rest_food.states.utils import validate_phone_number


logger = logging.getLogger(__name__)


def parse_data(data) -> Command:
    parts = data.split('|')

    logger.info(parts)

    return Command(command=DemandCommandName(parts[0]), arguments=parts[1:])


def handle_demand_data(user: User, data: str):
    return _handle(user, parse_data(data))


def _get_next_command(user: User) -> Command:
    logger.info('User context: %s', user.context)

    return Command(
        command=DemandCommandName(user.context['next_command']),
        arguments=user.context['arguments'],
    )


def _handle(user: User, command: Command):
    return COMMAND_HANDLERS[command.command](user, *command.arguments)


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
        'text': _('Confirm and take products'),
        'data': f'{DemandCommandName.FINISH_TAKE.value}|'
                f'{provider_str}|{supply_user_db_id}|{message_id}',
    }, {
        'text': _('Cancel'),
        'data': f'{DemandCommandName.CANCEL_TAKE.value}',
    }])

    return Reply(
        text=_('Please, confirm/edit your contact information to proceed.'),
        buttons=buttons,
    )


def _get_review_buttons(user: User):
    buttons = [{
        'text': _('Name: {}').format(user.info["name"]),
        'data': f'{DemandCommandName.EDIT_NAME.value}',
    }]

    if user.info['username']:
        if user.info['display_username']:
            buttons.append({
                'text': _('Connect via {}: ✅').format(user.provider.value),
                'data': f'{DemandCommandName.DISABLE_USERNAME.value}',
            })
        else:
            buttons.append({
                'text': ('Connect via {}: ❌').format(user.provider.value),
                'data': DemandCommandName.ENABLE_USERNAME.value,
            })

    buttons.append({
        'text': _('Phone: %s') % (user.info.get(UserInfoField.PHONE.value) or 'not set'),
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
        return Reply(text=_('Someone has already taken it.'))

    notify_supply_for_booked(
        supply_user=supply_user,
        message_id=message_id,
        demand_user=user
    )

    message = _("{name} is notified that you'll take it.\n"
                "Address: {address}\n").format(
        name=supply_user.info['name'],
        address=supply_user.info['address'],
    )

    return Reply(text=message)


def _handle_info(user: User, provider_str: str, supply_user_db_id: str, message_id: str):
    supply_user = get_user(
        supply_user_db_id,
        provider=Provider(provider_str),
        workflow=Workflow.SUPPLY
    )

    if supply_user is None:
        return Reply(_('Information was not found.'))

    info = _(
        "Restaurant name: {name}\n"
        "Address: {address}"
    ).format(
        name=supply_user.info['name'],
        address=supply_user.info['address'],
    )

    db_message = get_supply_message_record(user=supply_user, message_id=message_id)

    if db_message.demand_user_id is not None:
        return Reply(text=_("SOMEONE HAS ALREADY TAKEN IT! (maybe you)\n\n{}").format(info))

    coordinates = supply_user.info[UserInfoField.COORDINATES.value]

    return Reply(
        text=info,
        coordinates=coordinates,
        buttons=[[
            {
                'text': _('Take it'),
                'data': f'{DemandCommandName.TAKE.value}|'
                        f'{supply_user.provider.value}|'
                        f'{supply_user.user_id}|'
                        f'{message_id}',
            },
        ], [
            {
                'text': _('Map'),
                'url': f'geo://{coordinates[0]},{coordinates[1]}',
            }
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


def _handle_edit_name(user: User):
    return Reply(next_state=DemandState.EDIT_NAME)


def _handle_edit_phone(user: User):
    return Reply(next_state=DemandState.EDIT_PHONE)


def _handle_cancel_command(user: User):
    logger.info('Remove the "Edit info" message instead.')
    return Reply(text=_('Cancelled.'))


COMMAND_HANDLERS = {
    DemandCommandName.TAKE: _handle_take,
    DemandCommandName.INFO: _handle_info,
    DemandCommandName.ENABLE_USERNAME: _handle_enable_username,
    DemandCommandName.DISABLE_USERNAME: _handle_disable_username,
    DemandCommandName.FINISH_TAKE: _handle_finish_take,
    DemandCommandName.EDIT_NAME: _handle_edit_name,
    DemandCommandName.EDIT_PHONE: _handle_edit_phone,
    DemandCommandName.CANCEL_TAKE: _handle_cancel_command,
}


class BaseSetInfoState(State):
    _intro_text = None  # type: str
    _info_field = None  # type: UserInfoField

    def _build_cancellable_message(self, text):
        next_command = _get_next_command(self.db_user)

        return Reply(
            text=text,
            buttons=[[{
                'text': _('Cancel'),
                'data': '{}|{}'.format(
                    next_command.command.value,
                    '|'.join(next_command.arguments)
                ),
            }]],
        )

    def get_intro(self):
        return self._build_cancellable_message(self._intro_text)

    def handle(self, text: str, *args, **kwargs):
        set_info(self.db_user, self._info_field, text)
        return _handle(self.db_user, _get_next_command(self.db_user))


class SetNameState(BaseSetInfoState):
    _intro_text = _('Enter your name:')
    _info_field = UserInfoField.NAME


class SetPhoneState(BaseSetInfoState):
    _intro_text = _('Enter your phone number:')
    _info_field = UserInfoField.PHONE

    def handle(self, text: str, *args, **kwargs):
        try:
            validate_phone_number(text)
        except ValidationError as e:
            return self._build_cancellable_message(e.message)

        return super().handle(text)


class DefaultState(State):
    def handle(self, *args, **kwargs) -> Reply:
        return Reply(text=_('Hello. Here you will see notifications about available food.'))


