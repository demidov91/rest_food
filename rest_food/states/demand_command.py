import logging

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
    SocialStatus,
    soc_status_translation,
    translate_social_status_string,
)
from rest_food.translation import translate_lazy as _
from rest_food.states.utils import (
    build_food_message_by_id,
    get_next_command,
    get_demand_back_button,
)

logger = logging.getLogger(__name__)


def parse_data(data) -> Command:
    parts = data.split('|')

    logger.info(parts)

    return Command(name=parts[0], arguments=parts[1:])


def handle_demand_data(user: User, data: str):
    return handle(user, parse_data(data))


def handle(user: User, command: Command):
    return COMMAND_HANDLERS[DemandCommandName(command.name)](user, *command.arguments)


def _handle_take(user: User, provider_str: str, supply_user_db_id: str, message_id: str):
    set_next_command(
        user,
        Command(
            name=DemandCommandName.TAKE.value,
            arguments=[provider_str, supply_user_db_id, message_id],
        )
    )

    buttons = _get_review_buttons(user)
    buttons.extend([
        [{
            'text': _('Confirm and take products'),
            'data': f'{DemandCommandName.FINISH_TAKE.value}|'
                    f'{provider_str}|{supply_user_db_id}|{message_id}',
        }],
        [{
            'text': _('Cancel'),
            'data': f'{DemandCommandName.INFO.value}|'
                    f'{provider_str}|{supply_user_db_id}|{message_id}',
        }]
    ])

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
                'text': _('Connect via {}: ❌').format(user.provider.value),
                'data': DemandCommandName.ENABLE_USERNAME.value,
            })

    buttons.append({
        'text': (
            _('Social status: %s') %
            translate_social_status_string(user.info.get(UserInfoField.SOCIAL_STATUS.value))
        ),
        'data': DemandCommandName.EDIT_SOCIAL_STATUS.value,
    })

    buttons.append({
        'text': _('Phone: %s') % (user.info.get(UserInfoField.PHONE.value) or _('not set')),
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

    logger.info("message_id=%s", message_id)

    info = _(
        "Restaurant name: {name}\n"
        "Address: {address}\n"
        "Phone: {phone}\n"
        "\n\n"
        "{products}"
    ).format(
        name=supply_user.info[UserInfoField.NAME.value],
        address=supply_user.info[UserInfoField.ADDRESS.value],
        phone=supply_user.info[UserInfoField.PHONE.value],
        products=build_food_message_by_id(user=supply_user, message_id=message_id),
    )

    db_message = get_supply_message_record(user=supply_user, message_id=message_id)

    if db_message.demand_user_id is not None:
        return Reply(text=_("SOMEONE HAS ALREADY TAKEN IT! (maybe you)\n\n{}").format(info))

    coordinates = supply_user.approved_coordinates()

    take_it_button = {
        'text': _('Take it'),
        'data': f'{DemandCommandName.TAKE.value}|'
                f'{supply_user.provider.value}|'
                f'{supply_user.user_id}|'
                f'{message_id}',
    }


    if not coordinates:
        return Reply(
            text=info,
            buttons=[[take_it_button]]
        )

    return Reply(
        text=info,
        coordinates=coordinates,
        buttons=[
            [take_it_button],
            [{
                'text': _('Map'),
                'url': f'https://dzmitry.by/redirect?to=geo:{coordinates[0]},{coordinates[1]}?z=21',
            }]
        ]
    )


def _handle_enable_username(user: User):
    set_info(user, UserInfoField.DISPLAY_USERNAME, True)
    command = get_next_command(user)
    return handle(user, command)


def _handle_disable_username(user: User):
    set_info(user, UserInfoField.DISPLAY_USERNAME, False)
    command = get_next_command(user)
    return handle(user, command)


def _handle_set_social_status(user: User, social_status: str):
    set_info(user, UserInfoField.SOCIAL_STATUS, social_status)
    command = get_next_command(user)
    return handle(user, command)


def _handle_edit_name(user: User):
    return Reply(next_state=DemandState.EDIT_NAME)


def _handle_edit_phone(user: User):
    return Reply(next_state=DemandState.EDIT_PHONE)


def _handle_edit_social_status(user: User):
    buttons = [[
        {
            'text': soc_status_translation.get(x) or '~~',
            'data': f'{DemandCommandName.SET_SOCIAL_STATUS.value}|{x.value}',
        }] for x in SocialStatus
    ]

    buttons.append([get_demand_back_button(user)])

    return Reply(text=_('Choose your social status:'), buttons=buttons)


COMMAND_HANDLERS = {
    DemandCommandName.TAKE: _handle_take,
    DemandCommandName.INFO: _handle_info,
    DemandCommandName.ENABLE_USERNAME: _handle_enable_username,
    DemandCommandName.DISABLE_USERNAME: _handle_disable_username,
    DemandCommandName.FINISH_TAKE: _handle_finish_take,
    DemandCommandName.EDIT_NAME: _handle_edit_name,
    DemandCommandName.EDIT_PHONE: _handle_edit_phone,
    DemandCommandName.EDIT_SOCIAL_STATUS: _handle_edit_social_status,
    DemandCommandName.SET_SOCIAL_STATUS: _handle_set_social_status,
}








