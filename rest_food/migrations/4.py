from rest_food.db import db, _update_message

from rest_food.common.constants import DT_DB_FORMAT
import datetime


def forward():
    for message in db.messages.find({'dt_published': {'$exists': True}}):
        print('apply')
        _update_message(
            message['_id'],
            update={
                'dt_published': datetime.datetime.strptime(
                    message['dt_published'], '%Y%m%d%H%M%S'
                ).strftime(DT_DB_FORMAT)
            },
        )


def backward():
    for message in db.messages.find({'dt_published': {'$exists': True}}):
        _update_message(
            message['_id'],
            update={
                'dt_published': datetime.datetime.strptime(
                    message['dt_published'], '%Y-%m-%d %H:%M:%S'
                ).strftime('%Y%m%d%H%M%S')
            },
        )