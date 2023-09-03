from typing import Optional

from rest_food.common.shared_commands import choose_language, handle_delete
from rest_food.enums import SupplyTgCommand, SupplyState, Provider
from rest_food.entities import User, Reply
from rest_food.state_machine import set_supply_state
from rest_food.supply.supply_state import DefaultState


def handle_supply_tg_command(user: User, command: SupplyTgCommand) -> Optional[Reply]:
    match command:
        case SupplyTgCommand.START:
            state = DefaultState(db_user=user, provider=Provider.TG)
            reply = state.get_intro()
            reply.next_state = state.get_next_state()
            return reply

        case SupplyTgCommand.LANGUAGE:
            set_supply_state(user, None)
            reply = choose_language(user)
            reply.next_state = SupplyState.NO_STATE
            return reply

        case SupplyTgCommand.DELETE:
            set_supply_state(user, None)
            reply = handle_delete(user)
            reply.next_state = SupplyState.NO_STATE
            return reply
