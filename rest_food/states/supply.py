from typing import Optional

from rest_food.states.base import State
from rest_food.entities import Reply, SupplyState, Provider, UserInfoField
from rest_food.db import (
    extend_supply_message,
    create_supply_message,
    cancel_supply_message,
    set_supply_message_time,
    set_info,
)
from rest_food.communication import publish_supply_event
from rest_food.translation import translate_lazy as _
from .utils import build_active_food_message


class ForceInfoMixin:
    def get_next_state(self):
        for field, state in (
                ('name', SupplyState.FORCE_NAME),
                ('address', SupplyState.FORCE_ADDRESS),
                ('phone', SupplyState.FORCE_PHONE),
        ):
            if not self.db_user.info.get(field):
                return state

        return SupplyState.READY_TO_POST


class DefaultState(ForceInfoMixin, State):
    def handle(self, text: str, data: str):
        return Reply(
            text=_('Please, provide information about yourself before getting started'),
            next_state=self.get_next_state()
        )


class ReadyToPostState(State):
    intro = Reply(
        buttons=[
            [{
                'text': _('Edit restaurant info'),
                'data': 'view-info',
            }],
        ],
        text=_('Enter food you can share and click "send"'),
    )

    def handle(self, text: str, data: str):
        if data == 'view-info':
            return Reply(next_state=SupplyState.VIEW_INFO)

        create_supply_message(self.db_user, text, provider=self.provider)
        return Reply(next_state=SupplyState.POSTING)


class PostingState(State):
    intro = Reply(
        buttons=[[
            {
                'text': _('Set time and send'),
                'data': 'set-time',
            },
            {
                'text': _('Cancel'),
                'data': 'cancel',
            }
        ]]
    )

    def get_intro(self):
        reply = super().get_intro()
        reply.text = _('Food you can share:\n{}').format(build_active_food_message(self.db_user))
        return reply

    def handle(self, text: str, data: str):
        if data == 'set-time':
            return Reply(next_state=SupplyState.SET_TIME)

        if data == 'cancel':
            cancel_supply_message(self.db_user, provider=self.provider)
            return Reply(
                text=_('Product list is cleared.'),
                next_state=SupplyState.READY_TO_POST,
            )

        if text:
            extend_supply_message(self.db_user, text, provider=self.provider)


class SetMessageTimeState(State):
    intro = Reply(
        text=_('Specify the time'),
        buttons=[
            [{
                'text': _('Cancel'),
                'data': 'cancel',
            }],
        ]
    )

    def handle(self, text: str, data: str):
        if data == 'cancel':
            cancel_supply_message(self.db_user, provider=self.provider)
            return Reply(
                text=_('Product list is cleared.'),
                next_state=SupplyState.READY_TO_POST,
            )

        if text:
            set_supply_message_time(self.db_user, text)
            publish_supply_event(self.db_user)
            return Reply(
                text=_(
                    "Information is sent. "
                    "I'll notify you when there is someone to take this food."
                ),
                next_state=SupplyState.READY_TO_POST,
            )


class ViewInfoState(State):
    def __init__(self, db_user, *, provider: Provider=Provider.TG):
        super().__init__(db_user, provider=provider)

    def get_intro(self):
        return Reply(
            text=_('You can edit your contact info here'),
            buttons=[
                [{
                    'text': _('Name: %s') % self.db_user.info['name'],
                    'data': 'edit-name',
                }],
                [{
                    'text': _('Address: %s') % self.db_user.info['address'],
                    'data': 'edit-address',
                }],
                [{
                    'text': _('Phone: %s') % self.db_user.info['phone'],
                    'data': 'edit-phone',
                },{
                    'text': _('Back'),
                    'data': 'back',
                }],
            ]
        )

    def handle(self, text: str, data: Optional[str]):
        if data == 'edit-name':
            return Reply(next_state=SupplyState.EDIT_NAME)

        if data == 'edit-address':
            return Reply(next_state=SupplyState.EDIT_ADDRESS)

        if data == 'edit-phone':
            return Reply(next_state=SupplyState.EDIT_PHONE)

        if data == 'back':
            return Reply(next_state=SupplyState.READY_TO_POST)


class BaseEditInfoState(State):
    _message = None         # type: str
    _info_to_edit = None    # type: UserInfoField

    def get_intro(self):
        reply = Reply(text=self._message)
        if self._info_to_edit in self.db_user.info:
            reply.buttons = [[{
                'text': _('Cancel'),
                'data': 'cancel',
            }]]

        return reply

    def get_next_state(self):
        return SupplyState.VIEW_INFO

    def handle(self, text: str, data: Optional[str]):
        if data == 'cancel':
            return Reply(next_state=SupplyState.VIEW_INFO)

        set_info(self.db_user, self._info_to_edit, text)

        return Reply(next_state=self.get_next_state())


class SetNameState(BaseEditInfoState):
    _message = _('Please, enter name of the restaurant.')
    _info_to_edit = UserInfoField.NAME


class SetAddressState(BaseEditInfoState):
    _message = _('Please, provide restaurant address.')
    _info_to_edit = UserInfoField.ADDRESS


class SetPhoneState(BaseEditInfoState):
    _message = _('Please, enter contact phone number.')
    _info_to_edit = UserInfoField.PHONE


class ForceSetNameState(ForceInfoMixin, SetNameState):
    pass


class ForceSetAddressState(ForceInfoMixin, SetAddressState):
    pass


class ForceSetPhoneState(ForceInfoMixin, SetPhoneState):
    pass
