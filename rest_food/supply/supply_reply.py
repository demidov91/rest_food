from rest_food.entities import User, Reply
from rest_food.enums import SupplyCommand
from rest_food.common.formatters import (
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
            'data': SupplyCommand.CANCEL_BOOKING.build(message_id),
        }, {
            'text': _('Approve'),
            'data': SupplyCommand.APPROVE_BOOKING.build(message_id),
        }],
        [{
            'text': _('View all messages'),
            'data': SupplyCommand.LIST_MESSAGES.build(),
        }],
    ]

    return Reply(text=message, buttons=buttons)


def build_new_supplier_notification(supply_user: User) -> Reply:
    return Reply(
        text=build_new_supplier_notification_text(supply_user),
        buttons=[[{
            'text': _('Approve'),
            'data': SupplyCommand.APPROVE_SUPPLIER.build(supply_user.id),
        }, {
            'text': _('Decline'),
            'data': SupplyCommand.DECLINE_SUPPLIER.build(supply_user.id),
        }]]
    )