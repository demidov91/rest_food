

from rest_food.states.base import State
from rest_food.states import supply
from rest_food.db import get_user, set_state
from rest_food.entities import Provider, Workflow, SupplyState, DemandState, User


SUPPLY = {
    None: supply.DefaultState,
    SupplyState.READY_TO_POST: supply.ReadyToPostState,
    SupplyState.POSTING: supply.PostingState,
}


def get_supply_state(tg_user_id: int) -> State:
    user = get_user(tg_user_id, Provider.TG, Workflow.SUPPLY)
    return SUPPLY[SupplyState(user.state)](user)


def set_supply_state(db_id: str, state: SupplyState) -> State:
    set_state(db_id, state.value)
    return SUPPLY[state](User(id=db_id))


def get_demand_state(tg_user_id) -> State:
    pass


def set_demand_state(tg_user_id) -> State:
    pass


