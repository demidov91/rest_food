import json
import logging

import rest_food.settings
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
