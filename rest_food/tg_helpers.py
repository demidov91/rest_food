from decimal import Decimal
from typing import Optional, Tuple

from telegram.update import Update


def update_to_text(update: Update) -> Optional[str]:
    return update.message and (update.message.text or update.message.contact and update.message.contact.phone_number)


def update_to_coordinates(update: Update) -> Optional[Tuple[Decimal, Decimal]]:
    return (
            update.message and
            update.message.location and
            (
                Decimal(str(update.message.location.latitude)),
                Decimal(str(update.message.location.longitude))
            )
    )
