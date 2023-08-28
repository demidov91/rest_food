from rest_food.common.shared_commands import choose_language
from rest_food.enums import SupplyTgCommand, SupplyState
from rest_food.entities import User, Reply
from rest_food.state_machine import set_supply_state


def handle_supply_tg_command(user: User, command: SupplyTgCommand) -> Reply:
    set_supply_state(user, None)
    match command:
        case SupplyTgCommand.START:
            return Reply(next_state=SupplyState.READY_TO_POST)

        case SupplyTgCommand.LANGUAGE:
            reply = choose_language(user)
            reply.next_state = SupplyState.NO_STATE
            return reply
