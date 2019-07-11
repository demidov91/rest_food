import logging
from typing import Iterable

from rest_food.entities import Reply


logger = logging.getLogger(__name__)


def notify_admin(user):
    pass


def publish_supply_event(db_id: str):
    logger.info(f'Mock sending an event from {db_id}')


def send_messages(tg_user_id, replies:Iterable[Reply]):
    logger.info('Mock sending reply to {}:\n{}'.format(tg_user_id, '\n'.join(
        '{}|Buttons:{}'.format(x.text, x.buttons) for x in replies
    )))