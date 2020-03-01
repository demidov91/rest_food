from rest_food.db import db


def forward():
    for record in db.users.find({}):
        created_at = record['_id'].generation_time
        created_at = created_at.replace(tzinfo=None)

        update_doc = {
            'created_at': created_at,
        }

        if record.get('is_active'):
            update_doc['active_from'] = created_at
        elif record.get('is_active') is False:
            update_doc['inactive_from'] = created_at

        db.users.update_one({'_id': record['_id']}, {'$set': update_doc})


def backward():
    db.users.update({}, {'$unset': {
        'created_at': '',
        'active_from': '',
        'inactive_from': '',
    }}, multi=True)
