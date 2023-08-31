from rest_food.common.shared_commands import choose_language
from rest_food.demand.demand_command import handle_parsed_command, _choose_location
from rest_food.entities import User, Reply
from rest_food.enums import DemandTgCommand, DemandCommand
from rest_food.state_machine import set_demand_state


def handle_demand_tg_command(user: User, command: DemandTgCommand) -> Reply:
    set_demand_state(user, None)
    match command:
        case DemandTgCommand.START:
            return handle_parsed_command(user, DemandCommand.DEFAULT)

        case DemandTgCommand.LANGUAGE:
            return choose_language(user)

        case DemandTgCommand.LOCATION:
            return handle_parsed_command(user, DemandCommand.CHOOSE_LOCATION)
