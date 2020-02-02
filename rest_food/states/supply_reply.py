from rest_food.entities import User, SupplyCommand, Reply, UserInfoField
from rest_food.states.formatters import (
    build_demanded_message_text,
    build_new_supplier_notification_text,
)
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


def build_new_supplier_notification(supply_user: User) -> Reply:
    return Reply(
        text=build_new_supplier_notification_text(supply_user),
        buttons=[[{
            'text': _('Approve'),
            'data': f'c|{SupplyCommand.APPROVE_SUPPLIER}|{supply_user.id}',
        }, {
            'text': _('Decline'),
            'data': f'c|{SupplyCommand.DECLINE_SUPPLIER}|{supply_user.id}',
        }]]
    )