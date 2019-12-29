import logging

from rest_food.communication import notify_supply_for_booked
from rest_food.db import (
    get_user,
    mark_message_as_booked,
    get_supply_message_record,
    set_info,
    set_next_command,
    get_supply_user)
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
    get_next_command,
    get_demand_back_button,
    build_demand_side_short_message, build_demand_side_full_message_text,
    build_demand_command_button, build_demand_side_full_message_text_by_id)

logger = logging.getLogger(__name__)


def parse_data(data) -> Command:
    parts = data.split('|')

    logger.info(parts)

    return Command(name=parts[0], arguments=parts[1:])


def handle_demand_data(user: User, data: str):
    return handle(user, parse_data(data))


def handle(user: User, command: Command):
    return COMMAND_HANDLERS[DemandCommandName(command.name)](user, *command.arguments)


def _handle_take(user: User, provider_str: str, supply_user_id: str, message_id: str):
    set_next_command(
        user,
        Command(
            name=DemandCommandName.TAKE.value,
            arguments=[provider_str, supply_user_id, message_id],
        )
    )
    supply_user = get_supply_user(supply_user_id, Provider(provider_str))
    coordinates = supply_user.approved_coordinates()

    buttons = _get_review_buttons(user)

    if coordinates is not None:
        buttons.append([{
            'text': _('🌍 Map'),
            'data': DemandCommandName.MAP.build(provider_str, supply_user_id, message_id),
        }])

    buttons.append([
        {
            'text': _('❌ Cancel'),
            'data': f'{DemandCommandName.SHORT_INFO.value}|'
                    f'{provider_str}|{supply_user_id}|{message_id}',
        },
        {
            'text': _('Confirm 🆗✅'),
            'data': f'{DemandCommandName.FINISH_TAKE.value}|'
                    f'{provider_str}|{supply_user_id}|{message_id}',
        }
    ])

    info = build_demand_side_full_message_text(
        supply_user,
        get_supply_message_record(user=supply_user, message_id=message_id)
    )

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
        'data': f'{DemandCommandName.EDIT_NAME.value}',
    }]

    if user.info[UserInfoField.USERNAME.value]:
        if user.info[UserInfoField.DISPLAY_USERNAME.value]:
            buttons.append({
                'text': _('Connect via {}: ✅').format(user.provider.value),
                'data': f'{DemandCommandName.DISABLE_USERNAME.value}',
            })
        else:
            buttons.append({
                'text': _('Connect via {}: ❌').format(user.provider.value),
                'data': DemandCommandName.ENABLE_USERNAME.value,
            })

    social_status_translated = translate_social_status_string(
        user.info.get(UserInfoField.SOCIAL_STATUS.value)
    )

    if social_status_translated is None:
        social_status_text = _('Social status: not set ❌')
    else:
        social_status_text = _('Social status: %s ✅') % social_status_translated

    buttons.append({
        'text': social_status_text,
        'data': DemandCommandName.EDIT_SOCIAL_STATUS.value,
    })

    phone = user.info.get(UserInfoField.PHONE.value)
    phone_verbose = phone + ' ✅' if phone else _('not set ❓')

    buttons.append({
        'text': _('Phone: %s') % phone_verbose,
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

    info = build_demand_side_full_message_text_by_id(supply_user, message_id)

    message = '{}\n--------\n\n{}'.format(
        _("Restaurant is notified that you'll take it."),
        info
    )

    return Reply(text=message)


def _handle_info(user: User, provider_str: str, supply_user_id: str, message_id: str):
    supply_user = get_user(
        supply_user_id,
        provider=Provider(provider_str),
        workflow=Workflow.SUPPLY
    )

    if supply_user is None:
        return Reply(_('Information was not found.'))

    set_next_command(
        user,
        Command(
            name=DemandCommandName.INFO.value,
            arguments=[provider_str, supply_user_id, message_id],
        )
    )

    message_record = get_supply_message_record(user=supply_user, message_id=message_id)
    info = build_demand_side_full_message_text(supply_user, message_record)

    if message_record.demand_user_id is not None:
        if message_record.demand_user_id.endswith(user.user_id):
            logger.warning('Viewing taken food info.')
            return Reply(text=_("You've already taken it.\n\n{}".format(info)))

        return Reply(text=_("SOMEONE HAS ALREADY TAKEN IT!\n\n{}").format(info))

    coordinates = supply_user.approved_coordinates()

    buttons = []

    if coordinates is not None:
        buttons.append([{
            'text': _('Map'),
            'data': DemandCommandName.MAP.build(provider_str, supply_user_id, message_id),
        }])

    take_it_button = {
        'text': _('Take it'),
        'data': f'{DemandCommandName.TAKE.value}|'
                f'{supply_user.provider.value}|'
                f'{supply_user.user_id}|'
                f'{message_id}',
    }
    back_button = {
        'text': _('Back'),
        'data': DemandCommandName.SHORT_INFO.build(provider_str, supply_user_id, message_id),
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


def _handle_map(user: User, supply_provider: str, supply_user_id: str, message_id: str):
    supply_user = get_supply_user(user_id=supply_user_id, provider=Provider(supply_provider))
    coordinates = supply_user.approved_coordinates()

    if coordinates is None:
        logger.error('Map is requested while coordinates where not set.')
        return Reply(text=_('Coordinates where not provided.'))

    map_links = [{
        'text': _('Open in app'),
        'url': f'https://dzmitry.by/redirect?to=geo:{coordinates[0]},{coordinates[1]}?z=21',
    }]

    back_command = get_next_command(user)
    take_button = None
    if back_command.name != DemandCommandName.TAKE.value:
        take_button = {
            'text': _('Take it'),
            'data': DemandCommandName.TAKE.build(supply_provider, supply_user_id, message_id),
        }

    action_links = [build_demand_command_button(_('Back'), back_command)]
    if take_button is not None:
        action_links.append(take_button)

    return Reply(
        coordinates=coordinates,
        buttons=[map_links, action_links]
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
    DemandCommandName.SHORT_INFO: _handle_short_info,
    DemandCommandName.MAP: _handle_map,
    DemandCommandName.ENABLE_USERNAME: _handle_enable_username,
    DemandCommandName.DISABLE_USERNAME: _handle_disable_username,
    DemandCommandName.FINISH_TAKE: _handle_finish_take,
    DemandCommandName.EDIT_NAME: _handle_edit_name,
    DemandCommandName.EDIT_PHONE: _handle_edit_phone,
    DemandCommandName.EDIT_SOCIAL_STATUS: _handle_edit_social_status,
    DemandCommandName.SET_SOCIAL_STATUS: _handle_set_social_status,
}








