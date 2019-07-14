from rest_food.states.base import State
from rest_food.states import supply
from rest_food.db import get_or_create_user, set_state
from rest_food.entities import Provider, Workflow, SupplyState, DemandState, User


SUPPLY = {
    None: supply.DefaultState,
    SupplyState.READY_TO_POST: supply.ReadyToPostState,
    SupplyState.POSTING: supply.PostingState,
}


def get_supply_state(*, tg_user_id: int, tg_user: dict, tg_chat_id: int) -> State:
    user = get_or_create_user(
        user_id=tg_user_id,
        chat_id=tg_chat_id,
        provider=Provider.TG,
        workflow=Workflow.SUPPLY
    )
    user.tg_user = tg_user
    return SUPPLY[user.state and SupplyState(user.state)](user)


def set_supply_state(user: User, state: SupplyState) -> State:
    set_state(
        user_id=user.user_id,
        provider=Provider.TG,
        workflow=Workflow.SUPPLY,
        state=state.value
    )
    return SUPPLY[state](user)
