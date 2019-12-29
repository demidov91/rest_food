from rest_food.entities import User, SupplyCommand, Reply
from rest_food.states.formatters import build_demanded_message_text
from rest_food.translation import translate_lazy as _


def build_supply_side_booked_message(*, demand_user: User, supply_user: User, message_id: str):
    message = build_demanded_message_text(
        demand_user=demand_user, supply_user=supply_user, message_id=message_id
    )

    buttons = [
        [{
            'text': _('Reject'),
            'data': f'c|{SupplyCommand.CANCEL_BOOKING}|{message_id}',
        }, {
            'text': _('Approve'),
            'data': f'c|{SupplyCommand.APPROVE_BOOKING}|{message_id}',
        }],
        [{
            'text': _('View all messages'),
            'data': f'c|{SupplyCommand.LIST_MESSAGES}',
        }],
    ]

    return Reply(text=message, buttons=buttons)
