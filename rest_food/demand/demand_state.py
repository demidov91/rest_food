from rest_food.communication import queue_messages
from rest_food.db import set_info, unset_info
from rest_food.entities import Reply
from rest_food.enums import Workflow, UserInfoField, DemandCommand
from rest_food.exceptions import ValidationError
from rest_food.common.state import State
from rest_food.demand.demand_command import handle_db_command, handle_parsed_command
from rest_food.demand.demand_utils import get_demand_back_button, get_next_command
from rest_food.common.validators import validate_phone_number
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

    def handle_pending_command(self):
        return handle_db_command(self.db_user, get_next_command(self.db_user))

    def handle(self, text: str, *args, **kwargs):
        set_info(self.db_user, self._info_field, text)
        return self.handle_pending_command()


class SetNameState(BaseSetInfoState):
    _intro_text = _('Enter your name:')
    _info_field = UserInfoField.NAME


class SetPhoneState(BaseSetInfoState):
    _info_field = UserInfoField.PHONE

    def get_intro(self) -> Reply:
        buttons = [[{'text': _('← Back')}, {'text': _('Send phone'), 'request_contact': True }]]

        if self._info_field.value in self.db_user.info:
            buttons[0].insert(1, {'text': _('❌ Delete')})

        return Reply(
            text=_('Send your phone number'),
            buttons=buttons,
            is_text_buttons=True,
        )

    def handle(self, text: str, *args, **kwargs):
        # Text response is required to clear telegram text keyboard.
        queue_messages(tg_chat_id=self.db_user.chat_id, replies=[Reply(text=_('OK ✅'))], workflow=Workflow.DEMAND)

        text = text or ''
        if text.startswith('❌'):
            unset_info(self.db_user, self._info_field)
            return self.handle_pending_command()

        if text.startswith('←'):
            return self.handle_pending_command()

        try:
            validate_phone_number(text)
        except ValidationError as e:
            return self._build_cancellable_message(e.message)

        return super().handle(text)


class DefaultState(State):
    def handle(self, *args, **kwargs) -> Reply:
        return handle_parsed_command(self.db_user, DemandCommand.DEFAULT)
