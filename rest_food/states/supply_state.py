import logging
from typing import Optional

from rest_food.states.base import State
from rest_food.entities import Reply, SupplyState, Provider, UserInfoField, SupplyCommand
from rest_food.exceptions import ValidationError
from rest_food.db import (
    extend_supply_message,
    create_supply_message,
    cancel_supply_message,
    set_message_time,
    set_info,
    cancel_booking,
    list_messages,
    set_message_publication_time,
    unset_info,
)
from rest_food.communication import (
    publish_supply_event,
    notify_demand_for_cancel,
    notify_admin_about_new_supply_user_if_necessary,
)
from rest_food.settings import FEEDBACK_TG_BOT
from rest_food.states.formatters import build_active_food_message
from rest_food.states.utils import (
    get_coordinates,
    validate_phone_number,
)
from rest_food.translation import translate_lazy as _


logger = logging.getLogger(__name__)


class ForceInfoMixin:
    def __init__(self, *args, **kwargs):
        super(ForceInfoMixin, self).__init__(*args, **kwargs)
        self._fields_to_check = dict((
            (UserInfoField.NAME, SupplyState.FORCE_NAME),
            (UserInfoField.ADDRESS, SupplyState.FORCE_ADDRESS),
            (UserInfoField.IS_APPROVED_COORDINATES, SupplyState.FORCE_COORDINATES),
        ))

    def get_next_state(self):
        for field, state in self._fields_to_check.items():
            if not self.db_user.info.get(field.value):
                return state

        return SupplyState.INITIAL_EDIT_PHONE


class DefaultState(ForceInfoMixin, State):
    def handle(self, *args, **kwargs):
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
    )

    def _get_intro_text(self):
        if self.db_user.info.get(UserInfoField.IS_APPROVED_SUPPLY.value):
            return _('Enter food you can share and click "send"')

        if self.db_user.info.get(UserInfoField.IS_APPROVED_SUPPLY.value) is False:
            return (
                _('Your account was declined. Please, contact %s for any clarifications.') %
                FEEDBACK_TG_BOT
            )

        notify_admin_about_new_supply_user_if_necessary(self.db_user)

        return (
            _("We'll notify you when your account is approved. Also, you can contact us with %s") %
            FEEDBACK_TG_BOT
        )

    def get_intro(self) -> Reply:
        reply = super().get_intro()
        reply.text = self._get_intro_text()

        messages = list_messages(self.db_user)
        if messages:
            reply.buttons.append([{
                'text': _('View posted products'),
                'data': f'c|{SupplyCommand.LIST_MESSAGES}',
            }])

        return reply

    def handle(self, text: str, data: str, *args, **kwargs):
        if data == 'view-info':
            return Reply(next_state=SupplyState.VIEW_INFO)

        if not text:
            return

        if not self.db_user.info.get(UserInfoField.IS_APPROVED_SUPPLY.value):
            return

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

    def handle(self, text: str, data: str, *args, **kwargs):
        if data == 'set-time':
            return Reply(next_state=SupplyState.SET_TIME)

        if data == 'cancel':
            cancel_supply_message(self.db_user, provider=self.provider)
            return Reply(
                text=_('Product list is cleared.'),
                next_state=SupplyState.READY_TO_POST,
            )

        if text:
            extend_supply_message(self.db_user, text)


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

    def handle(self, text: str, data: str, *args, **kwargs):
        if data == 'cancel':
            cancel_supply_message(self.db_user, provider=self.provider)
            return Reply(
                text=_('Product list is cleared.'),
                next_state=SupplyState.READY_TO_POST,
            )

        if text:
            if not self.db_user.info.get(UserInfoField.IS_APPROVED_SUPPLY.value):
                logger.warning(
                    'There is an attempt to post a message by user %s', self.db_user.user_id
                )
                cancel_supply_message(self.db_user, provider=self.provider)
                return Reply(next_state=SupplyState.READY_TO_POST)

            message_id = self.db_user.editing_message_id
            set_message_time(message_id, text)
            publish_supply_event(self.db_user)
            set_message_publication_time(message_id)
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
                    'text': _('Coordinates: %s') % (
                        '✅' if self.db_user.approved_coordinates() else '❌'
                    ),
                    'data': 'edit-coordinates',
                }],
                [{
                    'text': _('Phone: %s') % (self.db_user.info['phone'] if 'phone' in self.db_user.info else '❌'),
                    'data': 'edit-phone',
                },{
                    'text': _('Back'),
                    'data': 'back',
                }],
            ]
        )

    def handle(self, text: str, data: Optional[str], *args, **kwargs):
        if data == 'edit-name':
            return Reply(next_state=SupplyState.EDIT_NAME)

        if data == 'edit-address':
            return Reply(next_state=SupplyState.EDIT_ADDRESS)

        if data == 'edit-phone':
            return Reply(next_state=SupplyState.EDIT_PHONE)

        if data == 'edit-coordinates':
            return Reply(next_state=SupplyState.EDIT_COORDINATES)

        if data == 'back':
            return Reply(next_state=SupplyState.READY_TO_POST)


class BaseEditInfoState(State):
    _message = None         # type: str
    _info_to_edit = None    # type: UserInfoField

    def info_field_is_set(self) -> bool:
        return bool(self.db_user.info.get(self._info_to_edit.value))

    def get_intro(self) -> Reply:
        reply = Reply(text=self._message)
        if self.info_field_is_set():
            reply.buttons = [[{
                'text': _('Cancel'),
                'data': 'cancel',
            }]]

        return reply

    def get_next_state(self):
        return SupplyState.VIEW_INFO

    def handle_text(self, text):
        set_info(self.db_user, self._info_to_edit, text)
        return Reply(next_state=self.get_next_state())

    def handle(self, text: str, data: Optional[str]=None, coordinates: Optional[tuple]=None):
        if data == 'cancel':
            return Reply(next_state=SupplyState.VIEW_INFO)

        return self.handle_text(text)


class SetNameState(BaseEditInfoState):
    _message = _('Please, enter name of the restaurant.')
    _info_to_edit = UserInfoField.NAME


class SetAddressState(BaseEditInfoState):
    _message = _('Please, provide restaurant address.')
    _info_to_edit = UserInfoField.ADDRESS

    def get_next_state(self):
        if self.db_user.info.get(UserInfoField.IS_APPROVED_COORDINATES.value):
            return SupplyState.VIEW_INFO
        return SupplyState.EDIT_COORDINATES

    def handle_text(self, text):
        initial_address = self.db_user.info.get(UserInfoField.ADDRESS.value)
        if text != initial_address:
            coordinates = get_coordinates(text)
            set_info(self.db_user, UserInfoField.IS_APPROVED_COORDINATES, False)
            if coordinates:
                set_info(self.db_user, UserInfoField.COORDINATES, [str(x) for x in coordinates])

        return super().handle_text(text)


class SetPhoneState(BaseEditInfoState):
    _info_to_edit = UserInfoField.PHONE

    def get_intro(self) -> Reply:
        buttons = [[{'text': _('← Back')}, {'text': _('Send phone'), 'request_contact': True}]]

        if self.info_field_is_set():
            buttons[0].insert(1, {'text': _('❌ Delete')})

        return Reply(
            text=_('Please, send your contact number.'),
            buttons=buttons,
            is_text_buttons=True,
        )

    def handle_text(self, text):
        text = text or ''
        if text.startswith('❌'):
            unset_info(self.db_user, self._info_to_edit)
            return Reply(text=_('OK ✅'), next_state=self.get_next_state())

        if text.startswith('←'):
            return Reply(text=_('OK ✅'), next_state=self.get_next_state())

        try:
            validate_phone_number(text)
        except ValidationError as e:
            return Reply(text=e.message)

        reply = super().handle_text(text)
        reply.text = _('OK ✅')  # Text response is required to clear telegram text keyboard.
        return reply


class InitialSetPhoneState(SetPhoneState):
    def get_intro(self) -> Reply:
        buttons = [[{'text': _('❌ Dismiss')}, {'text': _('Send phone'), 'request_contact': True}]]

        return Reply(
            text=_('Please, send your contact number.'),
            buttons=buttons,
            is_text_buttons=True,
        )

    def get_next_state(self):
        return SupplyState.READY_TO_POST


class SetCoordinatesState(BaseEditInfoState):
    _info_to_edit = UserInfoField.IS_APPROVED_COORDINATES

    def get_intro(self):
        if (
                not self.db_user.info.get(UserInfoField.IS_APPROVED_COORDINATES.value) and
                self.db_user.info.get(UserInfoField.COORDINATES.value)
        ):
            return self._build_approve_intro()

        return self._build_set_intro()

    def _build_approve_intro(self):
        return Reply(
            coordinates=self.db_user.info[UserInfoField.COORDINATES.value],
            buttons=[
                [{
                    'text': _('No! Edit! 🌍'),
                    'data': 'change-coordinates',
                }],
                [{
                    'text': _('Yes! Approve ✅'),
                    'data': 'approve-coordinates',
                }],
                [{
                    'text': _('Cancel'),
                    'data': 'cancel',
                }]
            ])

    def _build_set_intro(self):
        reply = Reply(text=_('Please, send me your coordinates. (Attach -> Location)'))
        if self.info_field_is_set():
            reply.buttons = [[{
                'text': _('Cancel'),
                'data': 'cancel',
            }]]
        else:
            reply.buttons = [[{
                'text': _('Provide later'),
                'data': 'later',
            }]]

        return reply

    def handle_text(self, text):
        return

    def handle(self, text: str, data: Optional[str]=None, coordinates: Optional[tuple]=None):
        if data == 'change-coordinates':
            set_info(self.db_user, UserInfoField.COORDINATES, None)
            return

        if data == 'approve-coordinates':
            set_info(self.db_user, UserInfoField.IS_APPROVED_COORDINATES, True)
            return Reply(next_state=self.get_next_state())

        if data == 'later':
            set_info(self.db_user, UserInfoField.IS_APPROVED_COORDINATES, True)
            return Reply(next_state=self.get_next_state())

        if coordinates:
            set_info(self.db_user, UserInfoField.COORDINATES, [str(x) for x in coordinates])
            set_info(self.db_user, UserInfoField.IS_APPROVED_COORDINATES, True)
            return Reply(next_state=self.get_next_state())

        return super().handle(text, data)


class ForceSetNameState(ForceInfoMixin, SetNameState):
    pass


class ForceSetAddressState(ForceInfoMixin, SetAddressState):
    pass


class ForceSetCoordinatesState(ForceInfoMixin, SetCoordinatesState):
    pass


class BookingCancelReason(State):
    def get_intro(self) -> Reply:
        return Reply(
            text=_('What to tell the foodsaver?'),
            buttons=[[{
                'text': _('Back to the message'),
                'data': f'c|{SupplyCommand.SHOW_DEMANDED_MESSAGE}|'
                        f'{self.db_user.context["booking_to_cancel"]}'
            }]]
        )

    def handle(self, text: str, data=None, coordinates=None):
        notify_demand_for_cancel(
            supply_user=self.db_user,
            message_id=self.db_user.context['booking_to_cancel'],
            message=text
        )
        cancel_booking(
            supply_user=self.db_user, message_id=self.db_user.context['booking_to_cancel']
        )
        return Reply(text=_('Cancelled'), next_state=SupplyState.READY_TO_POST)


class NoState(State):
    intro = None

    def handle(
            self,
            text: str,
            data,
            coordinates
    ):
        return Reply(
            text=_('Sorry, something went wrong.'),
            next_state=SupplyState.READY_TO_POST
        )
