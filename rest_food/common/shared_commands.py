from rest_food.common.constants import LANG_TO_NAME
from rest_food.entities import Reply, User
from rest_food.enums import Workflow, SupplyCommand, DemandCommand
from rest_food.translation import LANGUAGES_SUPPORTED
from rest_food.translation import translate_lazy as _


def choose_language(user: User):
    if user.workflow == Workflow.SUPPLY:
        _command_class = SupplyCommand.SET_LANGUAGE
        _default_command = SupplyCommand.BACK_TO_POSTING

    else:
        _command_class = DemandCommand.SET_LANGUAGE
        _default_command = DemandCommand.DEFAULT

    buttons = [
        [{
            'text': name,
            'data': _command_class.build(lang),
        }] for lang, name in LANG_TO_NAME if lang in LANGUAGES_SUPPORTED
    ]
    buttons.append([{
        'text': _('Back'),
        'data': _default_command.build(),
    }])
    return Reply(text=_('Choose the bot language:'), buttons=buttons)