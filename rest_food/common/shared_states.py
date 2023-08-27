from typing import Optional

from .state import State
from ..entities import Reply
from ..enums import Workflow
from rest_food.translation import translate_lazy as _
from rest_food.enums import SupplyCommand, DemandCommand
from rest_food.translation import LANGUAGES_SUPPORTED


class SetLanguage(State):
    LANG_TO_NAME = [
        ('be', 'Беларуская мова'),
        ('uk', 'Українська мова'),
        ('pl', 'Język polski'),
        ('lt', 'Lietuvių kalba'),
        ('en', 'English language'),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.db_user.workflow == Workflow.SUPPLY:
            self._command_class = SupplyCommand.SET_LANGUAGE
            self._default_command = SupplyCommand.BACK_TO_POSTING

        else:
            self._command_class = DemandCommand.SET_LANGUAGE
            self._default_command = DemandCommand.DEFAULT

    def handle(
            self,
            text: str,
            data: Optional[str],
            coordinates: Optional[tuple]
    ) -> Reply:
        buttons = [
            [{
                'text': name,
                'data': self._command_class.build(lang),
            }] for lang, name in self.LANG_TO_NAME if lang in LANGUAGES_SUPPORTED
        ]
        buttons.append([{
            'text': _('Back'),
            'data': self._default_command.build(),
        }])
        return Reply(text=_('Choose the bot language:'), buttons=buttons)