import logging
from typing import List

from rest_food.db import set_booking_to_cancel
from rest_food.entities import Reply, SupplyState, User


logger = logging.getLogger(__name__)


class SupplyCommand:
    CANCEL_BOOKING = 'cancel_booking'
    BACK_TO_POSTING = 'back_to_posting'



def handle_supply_command(user: User, command_name: str, args: List[str]):
    """
    Handle direct stateless command.

    Returns
    -------
    Reply

    """
    logger.info('Command: %s, args: %s', command_name, args)

    return {
        SupplyCommand.CANCEL_BOOKING: cancel_booking,
        SupplyCommand.BACK_TO_POSTING: back_to_posting,
    }[command_name](user, *args)


def cancel_booking(user, booking_id: str):
    set_booking_to_cancel(user, booking_id)
    return Reply(next_state=SupplyState.BOOKING_CANCEL_REASON)


def back_to_posting(user):
    return Reply(next_state=SupplyState.READY_TO_POST)