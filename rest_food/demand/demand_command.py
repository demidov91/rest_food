import logging

from rest_food.communication import notify_supply_for_booked
from rest_food.db import (
    get_user,
    mark_message_as_booked,
    set_info,
    set_next_command,
    get_supply_user,
    get_supply_message_record_by_id,
    set_approved_language,
)
from rest_food.entities import (
    User,
    Reply,
    Command,
    soc_status_translation,
)
from rest_food.enums import DemandState, Provider, Workflow, SocialStatus, DemandCommand, UserInfoField
from rest_food.translation import translate_lazy as _
from rest_food.demand.demand_reply import (
    build_demand_side_short_message,
    MapInfoHandler,
    MapTakeHandler,
    build_demand_side_message_by_id, MapBookedHandler,
    build_food_taken_message,
)
from rest_food.common.formatters import build_demand_side_full_message_text
from rest_food.demand.demand_utils import (
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
    return COMMAND_HANDLERS[DemandCommand(command.name)](user, *command.arguments)


def _handle_take(user: User, provider_str: str, supply_user_id: str, message_id: str):
    message_record = get_supply_message_record_by_id(message_id=message_id)
    supply_user = get_supply_user(supply_user_id, Provider(provider_str))

    if message_record is None or supply_user is None:
        return Reply(_('Information was not found.'))

    info = build_demand_side_full_message_text(supply_user, message_record)

    if message_record.demand_user_id:
        return build_food_taken_message(user, message_record.demand_user_id, info)

    set_next_command(
        user,
        Command(
            name=DemandCommand.TAKE.value,
            arguments=[provider_str, supply_user_id, message_id],
        )
    )

    coordinates = supply_user.approved_coordinates()

    buttons = _get_review_buttons(user)

    if coordinates is not None:
        buttons.append([{
            'text': _('🌍 Map'),
            'data': DemandCommand.MAP_TAKE.build(provider_str, supply_user_id, message_id),
        }])

    buttons.append([
        {
            'text': _('❌ Cancel'),
            'data': DemandCommand.SHORT_INFO.build(provider_str, supply_user_id, message_id),
        },
        {
            'text': _('Confirm 🆗✅'),
            'data': DemandCommand.FINISH_TAKE.build(provider_str, supply_user_id, message_id),
        }
    ])

    return Reply(
        text=_('%(info)s\n-----------\n%(ask_for_approve)s') % {
            'info': info,
            'ask_for_approve': _('Please, confirm/edit your contact information to proceed.'),
        },
        buttons=buttons,
    )


def _get_review_buttons(user: User):
    buttons = [{
        'text': _('Name: {}').format(user.info["name"]),
        'data': f'{DemandCommand.EDIT_NAME.value}',
    }]

    if user.info[UserInfoField.USERNAME.value]:
        if user.info[UserInfoField.DISPLAY_USERNAME.value]:
            buttons.append({
                'text': _('Connect via {}: ✅').format(user.provider.value),
                'data': f'{DemandCommand.DISABLE_USERNAME.value}',
            })
        else:
            buttons.append({
                'text': _('Connect via {}: ❌').format(user.provider.value),
                'data': DemandCommand.ENABLE_USERNAME.value,
            })

    social_status_translated = user.get_translated_social_status()

    if social_status_translated is None:
        social_status_text = _('Social status: not set ❌')
    else:
        social_status_text = _('Social status: %s ✅') % social_status_translated

    buttons.append({
        'text': social_status_text,
        'data': DemandCommand.EDIT_SOCIAL_STATUS.value,
    })

    phone = user.info.get(UserInfoField.PHONE.value)
    phone_verbose = phone + ' ✅' if phone else _('not set ❓')

    buttons.append({
        'text': _('Phone: %s') % phone_verbose,
        'data': f'{DemandCommand.EDIT_PHONE.value}',

    })

    return [[x] for x in buttons]


def _handle_finish_take(user: User, provider_str: str, supply_user_db_id: str, message_id: str):
    supply_user = get_user(
        supply_user_db_id,
        provider=Provider(provider_str),
        workflow=Workflow.SUPPLY
    )

    is_successfully_booked = mark_message_as_booked(
        demand_user=user, message_id=message_id
    )

    if not is_successfully_booked:
        return Reply(text=_('Someone has already taken it.'))

    notify_supply_for_booked(
        supply_user=supply_user,
        message_id=message_id,
        demand_user=user
    )

    return Reply(
        text=_("%s is notified that you'll take the food. Please, wait for approval.") %
             supply_user.info[UserInfoField.NAME.value]
    )


def _handle_info(user: User, provider_str: str, supply_user_id: str, message_id: str):
    supply_user = get_user(
        supply_user_id,
        provider=Provider(provider_str),
        workflow=Workflow.SUPPLY
    )
    message_record = get_supply_message_record_by_id(message_id=message_id)

    if supply_user is None or message_record is None:
        return Reply(_('Information was not found.'))

    info = build_demand_side_full_message_text(supply_user, message_record)

    if message_record.demand_user_id is not None:
        return build_food_taken_message(user, message_record.demand_user_id, info)

    set_next_command(
        user,
        Command(
            name=DemandCommand.INFO.value,
            arguments=[provider_str, supply_user_id, message_id],
        )
    )

    coordinates = supply_user.approved_coordinates()

    buttons = []

    if coordinates is not None:
        buttons.append([{
            'text': _('🌍 Map'),
            'data': DemandCommand.MAP_INFO.build(provider_str, supply_user_id, message_id),
        }])

    take_it_button = {
        'text': _('Take it'),
        'data': DemandCommand.TAKE.build(supply_user.provider.value, supply_user.user_id, message_id),
    }
    back_button = {
        'text': _('Back'),
        'data': DemandCommand.SHORT_INFO.build(provider_str, supply_user_id, message_id),
    }
    buttons.append([back_button, take_it_button])

    return Reply(
        text=info,
        buttons=buttons
    )


def _handle_short_info(user: User, supply_provider: str, supply_user_id: str, message_id: str):
    supply_user = get_user(
        user_id=supply_user_id, provider=Provider(supply_provider), workflow=Workflow.SUPPLY
    )
    return build_demand_side_short_message(supply_user, message_id)


def _handle_booked(user: User, supply_provider: str, supply_user_id: str, message_id: str):
    supply_user = get_supply_user(user_id=supply_user_id, provider=Provider(supply_provider))
    return build_demand_side_message_by_id(supply_user, message_id, intro=_("You've booked this"))


def _handle_map_info(user: User, supply_provider: str, supply_user_id: str, message_id: str):
    return MapInfoHandler.create(supply_provider, supply_user_id).build(message_id)


def _handle_map_take(user: User, supply_provider: str, supply_user_id: str, message_id: str):
    return MapTakeHandler.create(supply_provider, supply_user_id).build(message_id)


def _handle_map_booked(user: User, supply_provider: str, supply_user_id: str, message_id: str):
    return MapBookedHandler.create(supply_provider, supply_user_id).build(message_id)


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
            'data': DemandCommand.SET_SOCIAL_STATUS.build(x.value),
        }] for x in SocialStatus
    ]

    buttons.append([get_demand_back_button(user)])

    return Reply(text=_('Choose your social status:'), buttons=buttons)


def _handle_set_language(user: User, language: str):
    set_approved_language(user, language)
    return Reply(next_state=None)


COMMAND_HANDLERS = {
    DemandCommand.TAKE: _handle_take,
    DemandCommand.INFO: _handle_info,
    DemandCommand.SHORT_INFO: _handle_short_info,
    DemandCommand.MAP_INFO: _handle_map_info,
    DemandCommand.MAP_TAKE: _handle_map_take,
    DemandCommand.MAP_BOOKED: _handle_map_booked,
    DemandCommand.ENABLE_USERNAME: _handle_enable_username,
    DemandCommand.DISABLE_USERNAME: _handle_disable_username,
    DemandCommand.FINISH_TAKE: _handle_finish_take,
    DemandCommand.BOOKED: _handle_booked,
    DemandCommand.EDIT_NAME: _handle_edit_name,
    DemandCommand.EDIT_PHONE: _handle_edit_phone,
    DemandCommand.EDIT_SOCIAL_STATUS: _handle_edit_social_status,
    DemandCommand.SET_SOCIAL_STATUS: _handle_set_social_status,
    DemandCommand.SET_LANGUAGE: _handle_set_language,
}
