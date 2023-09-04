import logging

from rest_food.communication import notify_supply_for_booked
from rest_food.db import (
    get_user,
    mark_message_as_booked,
    set_info,
    set_next_command,
    get_supply_user,
    get_supply_message_record_by_id,
    set_approved_language, delete_user,
)
from rest_food.entities import (
    User,
    Reply,
    Command,
    soc_status_translation,
)
from rest_food.enums import DemandState, Provider, Workflow, SocialStatus, DemandCommand, UserInfoField, DemandTgCommand
from rest_food.translation import translate_lazy as _, set_language
from rest_food.demand.demand_reply import (
    build_demand_side_short_message,
    MapInfoHandler,
    MapTakeHandler,
    build_demand_side_message_by_id, MapBookedHandler,
    build_food_taken_message, build_set_location_reply,
)
from rest_food.common.formatters import build_demand_side_full_message_text
from rest_food.demand.demand_utils import (
    get_next_command,
    get_demand_back_button,
)
from rest_food.common.constants import COUNTRIES, CITIES

logger = logging.getLogger(__name__)


def parse_data(data) -> Command:
    parts = data.split('|')

    logger.info(parts)

    return Command(name=parts[0], arguments=parts[1:])


def handle_demand_data(user: User, data: str):
    return handle_db_command(user, parse_data(data))


def handle_db_command(user: User, command: Command):
    return handle_parsed_command(user, DemandCommand(command.name), *command.arguments)


def handle_parsed_command(user: User, command: DemandCommand, *arguments):
    return COMMAND_HANDLERS[command](user, *arguments)


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
    return handle_db_command(user, command)


def _handle_disable_username(user: User):
    set_info(user, UserInfoField.DISPLAY_USERNAME, False)
    command = get_next_command(user)
    return handle_db_command(user, command)


def _handle_set_social_status(user: User, social_status: str):
    set_info(user, UserInfoField.SOCIAL_STATUS, social_status)
    command = get_next_command(user)
    return handle_db_command(user, command)


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
    set_language(language)
    return handle_parsed_command(user, DemandCommand.DEFAULT)


def _handle_intro(user: User):
    intro_text = _('This is a foodsharing bot. _intro_text_goes_here_\n')
    if user.get_info_field(UserInfoField.LOCATION) is None:
        buttons = [
            [{
                'text': city.name,
                'data': DemandCommand.SET_LOCATION.build(f'{city.country_code}:{city.code}'),
            }] for city in CITIES
        ]
        buttons.append([
            {
                'text': _('Other'),
                'data': DemandCommand.CHOOSE_OTHER_LOCATION.build(),
            }
        ])

    else:
        buttons = None

    return Reply(text=intro_text, buttons=buttons)


def _handle_default(user: User):
    if user.get_info_field(UserInfoField.LOCATION) is not None:
        return Reply(text=_('Hello. Here you will see notifications about available food.'))

    return handle_parsed_command(user, DemandCommand.INTRO)


def _handle_choose_location(user: User):
    buttons = [
        [{
            'text': city.name,
            'data': DemandCommand.SET_LOCATION.build(f'{city.country_code}:{city.code}'),
        }] for city in CITIES
    ]
    buttons.append([
        {
            'text': _('Back'),
            'data': DemandCommand.DEFAULT.build(),
        },
        {
            'text': _('Other'),
            'data': DemandCommand.CHOOSE_OTHER_LOCATION.build(),
        }
    ])

    return Reply(text=_('Choose your active area'), buttons=buttons)


def _handle_choose_other_location(user: User):
    buttons = [
        [{
            'text': country.name,
            'data': DemandCommand.SET_LOCATION.build(country.code),
        }] for country in COUNTRIES if country.code != 'other'
    ]
    buttons.append([
        {
            'text': _('Back'),
            'data': DemandCommand.CHOOSE_LOCATION.build(),
        }, {
            'text': _('Other'),
            'data': DemandCommand.SET_LOCATION.build('other'),
        },
    ])

    return Reply(
        text=_(
            "The bot is not active outside of those cities. "
            "We will notify you when anything new appears in your area."
        ),
        buttons=buttons,
    )


def _handle_set_location(user: User, location: str):
    """
    location: str
        location in a format {country code}:{city}
        For example, by:minsk for Minsk.
    """
    try:
        reply = build_set_location_reply(location)
    except ValueError:
        logger.exception(f'Failed to handle location {location}')
        return Reply(text=_("Sorry. Unexpected error happened. Please, try later."))

    set_info(user, UserInfoField.LOCATION, location)
    return reply


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
    DemandCommand.CHOOSE_LOCATION: _handle_choose_location,
    DemandCommand.CHOOSE_OTHER_LOCATION: _handle_choose_other_location,
    DemandCommand.SET_LOCATION: _handle_set_location,
    DemandCommand.DEFAULT: _handle_default,
    DemandCommand.INTRO: _handle_intro,
}
