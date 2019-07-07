

from rest_food.states.base import State
from rest_food.states import supply
from rest_food.db import get_user
from rest_food.entities import Provider, Workflow, SupplyState, DemandState, User


SUPPLY = {
    None: supply.DefaultState,
    SupplyState.POSTING: supply.PostingState,
}


def get_supply_state(tg_user_id: int) -> State:
    user = get_user(tg_user_id, Provider.TG, Workflow.SUPPLY)
    return SUPPLY[user.state](user)


def set_supply_state(tg_user_id) -> State:
    pass


def get_demand_state(tg_user_id) -> State:
    pass


def set_demand_state(tg_user_id) -> State:
    pass


