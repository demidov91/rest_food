from rest_food.enums import SupplyTgCommand, SupplyState
from rest_food.entities import User
from rest_food.state_machine import set_supply_state


def handle_supply_tg_command(user: User, command: SupplyTgCommand):
    match command:
        case SupplyTgCommand.START:
            return set_supply_state(user, None)

        case SupplyTgCommand.LANGUAGE:
            return set_supply_state(user, SupplyState.SET_LANGUAGE)
