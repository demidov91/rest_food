from rest_food.states.base import State
from rest_food.states import supply
from rest_food.state_enum import SupplyState, DemandState


SUPPLY = {
    None: supply.DefaultState,
    SupplyState.POSTING: supply.PostingState,
}


def get_supply_state(tg_user_id) -> State:
    pass


def get_demand_state(tg_user_id) -> State:
    pass