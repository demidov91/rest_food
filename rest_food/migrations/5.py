from rest_food.db import db
from rest_food.enums import MessageState


def forward():
    db.messages.update(
        {'demand_user_id': {'$exists': True}},
        {'$set': {'state': MessageState.BOOKED.value}},
        multi=True,
    )
    db.messages.update(
        {'dt_published': {'$exists': True}, 'demand_user_id': {'$exists': False}},
        {'$set': {'state': MessageState.PUBLISHED.value}},
        multi=True,
    )


def backward():
    db.messages.update({}, {'$unset': {'state': ''}}, multi=True)