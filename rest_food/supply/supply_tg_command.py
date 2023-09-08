from typing import Optional

from rest_food.common.shared_commands import choose_language, handle_delete
from rest_food.enums import SupplyTgCommand, SupplyState, Provider, SupplyCommand
from rest_food.entities import User, Reply
from rest_food.state_machine import set_supply_state
from rest_food.supply.supply_state import DefaultState, ForceInfoMixin
from rest_food.translation import translate_lazy as _


def handle_supply_tg_command(user: User, command: SupplyTgCommand) -> Optional[Reply]:
    set_supply_state(user, None)

    if command == SupplyTgCommand.START:
        possibly_next_state = DefaultState(db_user=user, provider=Provider.TG).get_next_state()

        if possibly_next_state in ForceInfoMixin.fields_to_check.values():
            buttons = [[{
                'text': _('Got it'),
                'data': SupplyCommand.SET_STATE.build(possibly_next_state),
            }]]

        else:
            buttons = [
                [{
                    'text': _('Edit restaurant info'),
                    'data': SupplyCommand.SET_STATE.build(SupplyState.VIEW_INFO),
                }],
                [{
                    'text': _('Go to product posting'),
                    'data': SupplyCommand.SET_STATE.build(possibly_next_state),
                }],
            ]

        return Reply(text=_('Hello. <Supply-side intro>'), buttons=buttons, next_state=SupplyState.NO_STATE)

    if command == SupplyTgCommand.LANGUAGE:
        set_supply_state(user, None)
        reply = choose_language(user)
        reply.next_state = SupplyState.NO_STATE
        return reply

    if command == SupplyTgCommand.DELETE:
        set_supply_state(user, None)
        reply = handle_delete(user)
        reply.next_state = SupplyState.NO_STATE
        return reply
