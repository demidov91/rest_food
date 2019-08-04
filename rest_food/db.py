import logging
from typing import List, Optional, Tuple
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from rest_food.entities import Provider, Workflow, User


logger = logging.getLogger(__name__)


def _build_user_cluster(provider: Provider, workflow: Workflow):
    return f'{provider.value}-{workflow.value}'


def _build_user(data: dict):
    return User(
        cluster=data['cluster'],
        user_id=data['user_id'],
        chat_id=data.get('chat_id'),
        state=data.get('bot_state'),
        info=data.get('info'),
        editing_message_id=data.get('editing_message_id'),
        workflow=Workflow(data.get('workflow')),
        provider=Provider(data.get('provider')),
    )


def get_user(user_id, provider: Provider, workflow: Workflow):
    cluster = _build_user_cluster(provider, workflow)

    table = _get_state_table()
    response = table.get_item(
        Key={'cluster': cluster, 'user_id': str(user_id)},
        ConsistentRead=True,
    )

    if 'Item' not in response:
        return None

    return _build_user(response['Item'])



def get_or_create_user(*, user_id, chat_id, provider: Provider, workflow: Workflow) -> User:
    user = get_user(user_id, provider, workflow)

    if user is None:
        user = User(user_id=user_id, chat_id=chat_id)
        _create_user(user, provider, workflow)

    return user


def _create_user(user: User, provider: Provider, workflow: Workflow):
    table = _get_state_table()
    cluster = _build_user_cluster(provider, workflow)
    table.put_item(Item={
        'cluster': cluster,
        'user_id': str(user.user_id),
        'chat_id': user.chat_id,
        'provider': provider.value,
        'workflow': workflow.value,
        'info': {},
    })


def get_demand_users():
    table = _get_state_table()
    yield from (_build_user(x) for x in table.query(
        KeyConditionExpression=Key('cluster').eq(_build_user_cluster(Provider.TG, Workflow.DEMAND))
    )['Items'])
    yield from (_build_user(x) for x in table.query(
        KeyConditionExpression=Key('cluster').eq(_build_user_cluster(Provider.VB, Workflow.DEMAND))
    )['Items'])


def set_state(*, user_id: str, provider: Provider, workflow: Workflow, state: str):
    table = _get_state_table()
    table.update_item(
        Key={'user_id': user_id, 'cluster': _build_user_cluster(provider, workflow)},
        UpdateExpression='SET bot_state = :state',
        ExpressionAttributeValues={':state': state},
    )


def set_info(user: User, info_field: str, data: str):
    table = _get_state_table()
    table.update_item(
        Key={'user_id': user.user_id, 'cluster': _build_user_cluster(user.provider, user.workflow)},
        UpdateExpression='SET info.#info_field = :data',
        AttributeExpressionNames={'#info_field': info_field},
        ExpressionAttributeValues={':data': data},
    )
    user.info[info_field] = data


def create_supply_message(user: User, message: str, *, provider: Provider):
    message_id = str(uuid4())
    message_table = _get_message_table()
    message_table.put_item(Item={
        'id': message_id,
        'user_id': f'{provider.value}|{user.user_id}',
        'products': [message],
    })

    state_table = _get_state_table()
    state_table.update_item(
        Key={
            'user_id': user.user_id,
            'cluster': _build_user_cluster(provider, Workflow.SUPPLY),
        },
        UpdateExpression="set editing_message_id = :new_message_guid",
        ExpressionAttributeValues={':new_message_guid': message_id},
    )
    user.editing_message_id = message_id

    return message_id


def extend_supply_message(user: User, message: str, *, provider:Provider):
    message_table = _get_message_table()
    message_table.update_item(
        Key={'id': user.editing_message_id, 'user_id': f'{provider.value}|{user.user_id}'},
        UpdateExpression="SET #p = list_append(#p, :new_item)",
        ExpressionAttributeNames={'#p': 'products'},
        ExpressionAttributeValues={':new_item': [message]},
        ReturnValues="UPDATED_NEW"
    )


def set_supply_message_time(user: User, time_message: str):
    message_table = _get_message_table()
    message_table.update_item(
        Key={'id': user.editing_message_id, 'user_id': f'{user.provider.value}|{user.user_id}'},
        UpdateExpression="SET time = :time",
        ExpressionAttributeValues={':new_item': [time_message]},
    )


def cancel_supply_message(user: User, *, provider:Provider):
    state_table = _get_state_table()
    state_table.update_item(
        Key={
            'user_id': user.user_id,
            'cluster': _build_user_cluster(provider, workflow=Workflow.SUPPLY),
        },
        UpdateExpression="set editing_message_id = :new_message_guid",
        ExpressionAttributeValues={':new_message_guid': None},
    )
    user.editing_message_id = None


def get_supply_editing_message(user: User) -> List[str]:
    if user.editing_message_id is None:
        return []

    return get_supply_message(user=user, message_id=user.editing_message_id)


def get_supply_message_record(*, user, message_id: str):
    table = _get_message_table()
    return table.get_item(
        Key={'id': message_id, 'user_id': f'{user.provider.value}|{user.user_id}'},
        ConsistentRead=True,
    )['Item']


def get_supply_message(*, user, message_id: str):
    return get_supply_message_record(user=user, message_id=message_id)['products']



def mark_message_as_booked(demand_user: User, supply_user:User, message_id: str):
    table = _get_message_table()
    user_extended_id = f'{demand_user.provider.value}|{demand_user.user_id}'

    try:
        table.update_item(
            Key={
                'user_id': f'{supply_user.provider.value}|{supply_user.user_id}',
                'id': message_id,
            },
            UpdateExpression="SET demand_user_id = :demand_user_extended_id",
            ExpressionAttributeValues={':demand_user_extended_id': user_extended_id},
            ConditionExpression='attribute_not_exists(demand_user_id)',
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            return False
        raise

    return True


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
                'AttributeName': 'cluster',
                'AttributeType': 'S',
            }, {
                'AttributeName': 'user_id',
                'AttributeType': 'S',
            }],
            KeySchema=[{
                'AttributeName': 'cluster',
                'KeyType': 'HASH',
            }, {
                'AttributeName': 'user_id',
                'KeyType': 'RANGE',
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
