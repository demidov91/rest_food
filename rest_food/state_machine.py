from telegram.user import User as TgUser

from rest_food.enums import SupplyState, DemandState, Provider, Workflow, UserInfoField
from rest_food.common.state import State
from rest_food.demand import demand_state
from rest_food.supply import supply_state
from rest_food.db import get_or_create_user, set_state
from rest_food.entities import User

SUPPLY = {
    None: supply_state.DefaultState,
    SupplyState.READY_TO_POST: supply_state.ReadyToPostState,
    SupplyState.POSTING: supply_state.PostingState,
    SupplyState.SET_TIME: supply_state.SetMessageTimeState,
    SupplyState.VIEW_INFO: supply_state.ViewInfoState,
    SupplyState.EDIT_NAME: supply_state.SetNameState,
    SupplyState.EDIT_LOCATION: supply_state.SetLocationState,
    SupplyState.EDIT_ADDRESS: supply_state.SetAddressState,
    SupplyState.EDIT_COORDINATES: supply_state.SetCoordinatesState,
    SupplyState.EDIT_PHONE: supply_state.SetPhoneState,
    SupplyState.FORCE_NAME: supply_state.ForceSetNameState,
    SupplyState.FORCE_LOCATION: supply_state.ForceSetLocationState,
    SupplyState.FORCE_ADDRESS: supply_state.ForceSetAddressState,
    SupplyState.FORCE_COORDINATES: supply_state.ForceSetCoordinatesState,
    SupplyState.INITIAL_EDIT_PHONE: supply_state.InitialSetPhoneState,
    SupplyState.BOOKING_CANCEL_REASON: supply_state.BookingCancelReason,
    SupplyState.NO_STATE: supply_state.NoState,
}

DEMAND = {
    None: demand_state.DefaultState,
    DemandState.EDIT_NAME: demand_state.SetNameState,
    DemandState.EDIT_PHONE: demand_state.SetPhoneState,
}


def get_supply_state(*, tg_user_id: int, tg_user: TgUser, tg_chat_id: int) -> State:
    user = get_or_create_user(
        user_id=tg_user_id,
        chat_id=tg_chat_id,
        provider=Provider.TG,
        workflow=Workflow.SUPPLY,
        info={
            UserInfoField.USERNAME.value: tg_user.username,
            UserInfoField.LANGUAGE.value: tg_user.language_code,
        },
    )
    user.tg_user = tg_user
    return SUPPLY[user.state and SupplyState(user.state)](user)


def get_demand_state(user: User) -> State:
    return DEMAND[user.state and DemandState(user.state)](user)


def set_supply_state(user: User, state: SupplyState) -> State:
    set_state(
        user_id=user.user_id,
        provider=Provider.TG,
        workflow=Workflow.SUPPLY,
        state=state and state.value
    )
    return SUPPLY[state](user)


def set_demand_state(user: User, state: DemandState) -> State:
    set_state(
        user_id=user.user_id,
        provider=Provider.TG,
        workflow=Workflow.DEMAND,
        state=state and state.value
    )
    user.state = state and state.value
    return DEMAND[state](user)
