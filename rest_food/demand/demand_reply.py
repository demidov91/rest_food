import logging

from rest_food.db import get_supply_user
from rest_food.entities import User, Reply
from rest_food.enums import Provider, DemandCommand, UserInfoField
from rest_food.common.formatters import build_short_message_text_by_id, \
    build_demand_side_full_message_text_by_id

from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


def build_demand_side_short_message(supply_user: User, message_id: str):
    text_message = build_short_message_text_by_id(message_id=message_id)
    return Reply(
        text=_('{} can share the following:\n{}').format(
            supply_user.info[UserInfoField.NAME.value], text_message
        ),
        buttons=[[{
            'text': _('Take it'),
            'data': DemandCommand.TAKE.build(
                supply_user.provider.value, supply_user.user_id, message_id
            ),
        }, {
            'text': _('Info'),
            'data': DemandCommand.INFO.build(
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
        'data': DemandCommand.MAP_BOOKED.build(
            supply_user.provider.value, supply_user.user_id, message_id
        ),
    }]])


def build_food_taken_message(user: User, demand_user_id: str, info: str):
    if demand_user_id.endswith(user.user_id):
        logger.warning('Viewing taken food info.')
        return Reply(text=_("You've already taken it.\n\n{}".format(info)))

    return Reply(text=_("SOMEONE HAS ALREADY TAKEN IT!\n\n{}").format(info))


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

        buttons = [self._get_action_buttons(message_id)]

        return Reply(coordinates=coordinates, buttons=buttons)


class MapInfoHandler(MapHandler):
    def _get_action_buttons(self, message_id: str):
        return [{
            'text': _('Back'),
            'data': DemandCommand.INFO.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }, {
            'text': _('Take it'),
            'data': DemandCommand.TAKE.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }]


class MapTakeHandler(MapHandler):
    def _get_action_buttons(self, message_id: str):
        return [{
            'text': _('Back'),
            'data': DemandCommand.INFO.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }]


class MapBookedHandler(MapHandler):
    def _get_action_buttons(self, message_id: str):
        return [{
            'text': _('Back'),
            'data': DemandCommand.BOOKED.build(
                self.supply_user.provider.value, self.supply_user.user_id, message_id
            )
        }]