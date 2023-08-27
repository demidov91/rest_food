from typing import Optional

from .state import State
from ..entities import Reply
from ..enums import Workflow
from rest_food.translation import translate_lazy as _
from rest_food.enums import SupplyCommand, DemandCommand


class SetLanguage(State):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.db_user.workflow == Workflow.SUPPLY:
            self._command_class = SupplyCommand.SET_LANGUAGE
            self._default_command = SupplyCommand.DEFAULT

        else:
            self._command_class = DemandCommand.SET_LANGUAGE
            self._default_command = DemandCommand.DEFAULT

    def handle(
            self,
            text: str,
            data: Optional[str],
            coordinates: Optional[tuple]
    ) -> Reply:
        return Reply(
            text=_('Choose the bot language:'),
            buttons=[
                [
                    {
                        'text': 'Беларуская мова',
                        'data': self._command_class.build('be'),
                    },
                    {
                        'text': 'Українська мова',
                        'data': self._command_class.build('uk'),
                    },
                    {
                        'text': 'Język polski',
                        'data': self._command_class.build('pl'),
                    },
                    {
                        'text': 'Lietuvių kalba',
                        'data': self._command_class.build('lt'),
                    },
                    {
                        'text': 'English language',
                        'data': self._command_class.build('en'),
                    },
                    {
                        'text': _('Back'),
                        'data': self._default_command.build(),
                    },
                ],
            ],
        )