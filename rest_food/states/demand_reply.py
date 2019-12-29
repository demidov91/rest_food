import logging

from rest_food.db import get_supply_user
from rest_food.entities import User, Reply, UserInfoField, DemandCommandName, Provider
from rest_food.states.formatters import build_short_message_text_by_id, \
    build_demand_side_full_message_text_by_id

from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


def build_demand_side_short_message(supply_user: User, message_id: str):
    text_message = build_short_message_text_by_id(user=supply_user, message_id=message_id)
    return Reply(
        text=_('{} can share the following:\n{}').format(
            supply_user.info[UserInfoField.NAME.value], text_message
        ),
        buttons=[[{
            'text': _('Take it'),
            'data': DemandCommandName.TAKE.build(
                supply_user.provider.value, supply_user.user_id, supply_user.editing_message_id
            ),
        }, {
            'text': _('Info'),
            'data': DemandCommandName.INFO.build(
                supply_user.provider.value, supply_user.user_id, message_id
            )
        }]],
    )


def build_demand_side_message_by_id(supply_user: User, message_id: str, *, intro: str=None):
    text = build_demand_side_full_message_text_by_id(supply_user, message_id)

    if intro:
        text = '{}\n------\n{}'.format(intro, text)

    return Reply(text=text, buttons=[[{
        'text': _('🌍 Map'),
        'data': DemandCommandName.MAP_BOOKED.build(
            supply_user.provider.value, supply_user.user_id, message_id
        ),
    }]])


class MapHandler:
    def __init__(self, supply_user):
        self.supply_user = supply_user

    @classmethod
    def create(cls, provider_str: str, supply_user_id: str):
        return cls(get_supply_user(user_id=supply_user_id, provider=Provider(provider_str)))

    def _get_action_buttons(self, message_id: str):
        return []

    def build(self, message_id: str):
        coordinates = self.supply_user.approved_coordinates()

        if coordinates is None:
            logger.error('Map is requested while coordinates where not set.')
            return Reply(text=_('Coordinates where not provided.'))

        buttons = [[{
            'text': _('Open in app'),
            'url': f'https://dzmitry.by/redirect?to=geo:{coordinates[0]},{coordinates[1]}?z=21',
        }]]

        buttons.append(self._get_action_buttons(message_id))

        return Reply(
            coordinates=coordinates,
            buttons=buttons
        )


class MapInfoHandler(MapHandler):
    def _get_action_buttons(self, message_id: str):
        return [{
            'text': _('Back'),
            'data': DemandCommandName.INFO.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }, {
            'text': _('Take it'),
            'data': DemandCommandName.TAKE.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }]


class MapTakeHandler(MapHandler):
    def _get_action_buttons(self, message_id: str):
        return [{
            'text': _('Back'),
            'data': DemandCommandName.INFO.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }]


class MapBookedHandler(MapHandler):
    def _get_action_buttons(self, message_id: str):
        return [{
            'text': _('Back'),
            'data': DemandCommandName.BOOKED.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }]