from rest_food.db import db


def forward():
    db.users.create_index('user_id')


def backward():
    db.users.remove_index('user_id')
