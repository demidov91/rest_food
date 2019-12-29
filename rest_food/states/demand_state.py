from rest_food.db import set_info
from rest_food.entities import Reply, UserInfoField
from rest_food.exceptions import ValidationError
from rest_food.states.base import State
from rest_food.states.demand_command import handle
from rest_food.states.utils import get_demand_back_button, get_next_command, validate_phone_number
from rest_food.translation import translate_lazy as _


class BaseSetInfoState(State):
    _intro_text = None  # type: str
    _info_field = None  # type: UserInfoField

    def _build_cancellable_message(self, text):
        return Reply(
            text=text,
            buttons=[[get_demand_back_button(self.db_user)]],
        )

    def get_intro(self):
        return self._build_cancellable_message(self._intro_text)

    def handle(self, text: str, *args, **kwargs):
        set_info(self.db_user, self._info_field, text)
        return handle(self.db_user, get_next_command(self.db_user))


class SetNameState(BaseSetInfoState):
    _intro_text = _('Enter your name:')
    _info_field = UserInfoField.NAME


class SetPhoneState(BaseSetInfoState):
    _intro_text = _('Enter your phone number:')
    _info_field = UserInfoField.PHONE

    def handle(self, text: str, *args, **kwargs):
        try:
            validate_phone_number(text)
        except ValidationError as e:
            return self._build_cancellable_message(e.message)

        return super().handle(text)


class DefaultState(State):
    def handle(self, *args, **kwargs) -> Reply:
        return Reply(text=_('Hello. Here you will see notifications about available food.'))