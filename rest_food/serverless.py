import json
import logging

from rest_food.message_queue import get_mass_queue, get_single_queue
from rest_food.handlers import tg_supply, tg_demand


logger = logging.getLogger(__name__)


def json_response(data: dict) -> dict:
    return {
        'statusCode': 200,
        'headers': {},
        'body': json.dumps(data, ensure_ascii=False, indent=2),
    }


def supply(event, context):
    logger.info(event['body'])
    return json_response(
        tg_supply(json.loads(event['body']))
    )


def demand(event, context):
    logger.info(event['body'])
    return json_response(
        tg_demand(json.loads(event['body']))
    )


def send_mass_messages(event, context):
    logger.info(event)
    for record in event['Records']:
        try:
            get_mass_queue().process(record['body'])
        except Exception:
            logger.exception('Send message event was processed with unexpected exception.')


def super_send_mass_messages(event, context):
    logger.info(event)
    for record in event['Records']:
        try:
            get_mass_queue().redestrib_super_batch(json.loads(record['body']))
        except Exception:
            logger.exception('Send message event was processed with unexpected exception.')


def send_single_message(event, context):
    logger.info(event)
    for record in event['Records']:
        try:
            get_single_queue().process(record['body'])
        except Exception:
            logger.exception('Send message event was processed with unexpected exception.')