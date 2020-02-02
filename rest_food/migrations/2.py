from rest_food.db import db


def forward():
    res = db.messages.update(
        {},
        {'$rename': {'dt_created': 'dt_published'}},
        multi=True
    )


def backward():
    db.messages.update(
        {},
        {'$rename': {'dt_published': 'dt_created'}},
        multi=True
    )
