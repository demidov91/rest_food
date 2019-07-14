from typing import List, Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from rest_food.entities import Provider, Workflow, User


def _build_identifier(user_id, provider: Provider, workflow: Workflow):
    return f'{provider.value}-{workflow.value}-{user_id}'


def get_user_by_id(db_id: str) -> Optional[User]:
    table = _get_state_table()
    response = table.get_item(
        Key={'id': db_id},
        ConsistentRead=True,
    )

    if 'Item' not in response:
        return None

    data = response['Item']
    return User(
        id=data['id'],
        user_id=data['user_id'],
        state=data.get('bot_state'),
        info=data.get('info'),
        editing_message_id=data.get('editing_message_id'),
    )


def get_user(user_id, provider: Provider, workflow: Workflow) -> User:
    user = get_user_by_id(_build_identifier(user_id, provider, workflow))

    if user is None:
        user = User(user_id=user_id)
        user.id = _create_user(user, provider, workflow)

    return user


def _create_user(user: User, provider: Provider, workflow: Workflow):
    table = _get_state_table()
    identifier = _build_identifier(user.user_id, provider, workflow)
    table.put_item(Item={
        'id': identifier,
        'user_id': user.user_id,
        'info': {
            'address': 'Minsk, Charužaj, 22',
            'time_to_visit': 'till 23:00',
            'name': 'Demo restaurant',
        },
    })
    return identifier


def get_supply_user(tg_user_id: int):
    user = get_user(tg_user_id, Provider.TG, Workflow.SUPPLY)
    if not user.info:
        return None

    return user


def set_state(db_id: str, state: str):
    table = _get_state_table()
    table.update_item(
        Key={'id': db_id},
        UpdateExpression='SET bot_state = :state',
        ExpressionAttributeValues={':state': state},
    )


def create_supply_message(user: User, message: str):
    message_id = str(uuid4())
    message_table = _get_message_table()
    message_table.put_item(Item={
        'id': message_id,
        'user_id': user.id,
        'products': [message],
    })

    state_table = _get_state_table()
    state_table.update_item(
        Key={'id': user.id},
        UpdateExpression="set editing_message_id = :new_message_guid",
        ExpressionAttributeValues={':new_message_guid': message_id},
    )
    user.editing_message_id = message_id

    return message_id


def extend_supply_message(user: User, message: str):
    message_table = _get_message_table()
    message_table.update_item(
        Key={'id': user.editing_message_id, 'user_id': user.id},
        UpdateExpression="SET #p = list_append(#p, :new_item)",
        ExpressionAttributeNames={'#p': 'products'},
        ExpressionAttributeValues={':new_item': [message]},
        ReturnValues="UPDATED_NEW"
    )


def cancel_supply_message(user: User):
    state_table = _get_state_table()
    state_table.update_item(
        Key={'id': user.id},
        UpdateExpression="set editing_message_id = :new_message_guid",
        ExpressionAttributeValues={':new_message_guid': None},
    )
    user.editing_message_id = None


def get_supply_editing_message(user: User) -> List[str]:
    if user.editing_message_id is None:
        return []

    table = _get_message_table()
    return table.get_item(
        Key={'id': user.editing_message_id, 'user_id': user.id},
        ConsistentRead=True,
    )['Item']['products']


_STATE_TABLE = 'food-state'
_MESSAGE_TABLE = 'food-message'


def _get_db():
    # if STAGE != 'local':
    #     return boto3.resource('dynamodb', region_name='eu-central-1')

    return boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='eu-central-1'
    )


def _get_state_table():
    """
    `identifier` is a `provider-workflow-user_id` string.
    """
    db = _get_db()

    try:
        db.meta.client.describe_table(TableName=_STATE_TABLE)
    except ClientError:
        return db.create_table(
            TableName=_STATE_TABLE,
            AttributeDefinitions=[{
                'AttributeName': 'id',
                'AttributeType': 'S',
            }],
            KeySchema=[{
                'AttributeName': 'id',
                'KeyType': 'HASH',
            }],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1,
            }
        )

    return db.Table(_STATE_TABLE)


def _get_message_table():
    db = _get_db()

    try:
        db.meta.client.describe_table(TableName=_MESSAGE_TABLE)
    except ClientError:
        return db.create_table(
            TableName=_MESSAGE_TABLE,
            AttributeDefinitions=[{
                'AttributeName': 'user_id',
                'AttributeType': 'S',
            }, {
                'AttributeName': 'id',
                'AttributeType': 'S',
            }],
            KeySchema=[{
                'AttributeName': 'user_id',
                'KeyType': 'HASH',
            }, {
                'AttributeName': 'id',
                'KeyType': 'RANGE',
            }],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1,
            }
        )

    return db.Table(_MESSAGE_TABLE)
