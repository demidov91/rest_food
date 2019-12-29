from rest_food.entities import User, Reply, UserInfoField, DemandCommandName
from rest_food.states.formatters import build_short_message_text_by_id, \
    build_demand_side_full_message_text_by_id

from rest_food.translation import translate_lazy as _


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
        'text': _('Map'),
        'data': DemandCommandName.MAP_AFTER_BOOKED.build(supply_user, message_id),
    }]])