import logging

from rest_food.entities import Command, User
from rest_food.enums import DemandCommand
from rest_food.translation import translate_lazy as _

logger = logging.getLogger(__name__)


def build_demand_command_button(text: str, command: Command):
    return {
        'text': text,
        'data': DemandCommand(command.name).build(*command.arguments),
    }


def get_demand_back_button(user: User, text: str=_('Back')):
    return build_demand_command_button(text, get_next_command(user))


def get_next_command(user: User) -> Command:
    logger.info('User context: %s', user.context)

    return Command(
        name=user.context['next_command'],
        arguments=user.context['arguments'],
    )
