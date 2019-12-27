import logging
import os
from typing import List, Optional, Tuple
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from rest_food.entities import Provider, Workflow, User, Message, UserInfoField, Command


is_aws = os.environ.get('STAGE') == 'LIVE'
logger = logging.getLogger(__name__)


def _build_user_cluster(provider: Provider, workflow: Workflow):
    return f'{provider.value}-{workflow.value}'


def _build_extended_id(user: User) -> str:
    return f'{user.provider.value}|{user.user_id}'


def _build_user(data: dict):
    return User(
        cluster=data['cluster'],
        user_id=data['user_id'],
        chat_id=data.get('chat_id'),
        state=data.get('bot_state'),
        info=data.get('info'),
        context=data.get('context'),
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



def get_or_create_user(
        *,
        user_id,
        chat_id,
        provider: Provider,
        workflow: Workflow,
        info: dict=None,
) -> User:
    user = get_user(user_id, provider, workflow)

    if user is None:
        info = info or {}
        info[UserInfoField.DISPLAY_USERNAME.value] = True
        user = User(user_id=user_id, chat_id=chat_id, info=info)
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
        'info': user.info,
        'context': {},
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
        Key={
            'user_id': str(user_id),
            'cluster': _build_user_cluster(provider, workflow),
        },
        UpdateExpression='SET bot_state = :state',
        ExpressionAttributeValues={':state': state},
    )


def set_info(user: User, info_field: UserInfoField, data):
    table = _get_state_table()
    table.update_item(
        Key={
            'user_id': str(user.user_id),
            'cluster': _build_user_cluster(user.provider, user.workflow),
        },
        UpdateExpression='SET info.#info_field = :data',
        ExpressionAttributeNames={'#info_field': info_field.value},
        ExpressionAttributeValues={':data': data},
    )
    user.info[info_field.value] = data


def set_next_command(user: User, command: Command):
    table = _get_state_table()
    table.update_item(
        Key={'user_id': str(user.user_id), 'cluster': _build_user_cluster(user.provider, user.workflow)},
        UpdateExpression='SET context.next_command = :next_command, '
                         'context.arguments = :arguments',
        ExpressionAttributeValues={
            ':next_command': command.command.value,
            ':arguments': command.arguments,
        },
    )
    user.context['next_command'] = command.command.value
    user.context['arguments'] = command.arguments


def set_booking_to_cancel(user: User, message_id: str):
    table = _get_state_table()
    table.update_item(
        Key={'user_id': str(user.user_id),
             'cluster': _build_user_cluster(user.provider, user.workflow)},
        UpdateExpression='SET context.booking_to_cancel = :btc',
        ExpressionAttributeValues={':btc': message_id},
    )
    user.context['booking_to_cancel'] = message_id


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
            'user_id': str(user.user_id),
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
        Key={'id': user.editing_message_id, 'user_id': _build_extended_id(user)},
        UpdateExpression="SET take_time = :take_time",
        ExpressionAttributeValues={':take_time': time_message},
    )


def cancel_supply_message(user: User, *, provider:Provider):
    state_table = _get_state_table()
    state_table.update_item(
        Key={
            'user_id': str(user.user_id),
            'cluster': _build_user_cluster(provider, workflow=Workflow.SUPPLY),
        },
        UpdateExpression="set editing_message_id = :new_message_guid",
        ExpressionAttributeValues={':new_message_guid': None},
    )
    user.editing_message_id = None


def get_supply_editing_message(user: User) -> Optional[Message]:
    if user.editing_message_id is None:
        return None

    return get_supply_message_record(user=user, message_id=user.editing_message_id)


def get_supply_message_record(*, user, message_id: str) -> Message:
    table = _get_message_table()
    record = table.get_item(
        Key={'id': message_id, 'user_id': _build_extended_id(user)},
        ConsistentRead=True,
    )['Item']

    return Message(
        demand_user_id=record.get('demand_user_id'),
        products=record.get('products'),
        take_time=record.get('take_time'),
    )


def mark_message_as_booked(demand_user: User, supply_user:User, message_id: str):
    table = _get_message_table()
    user_extended_id = _build_extended_id(demand_user)

    try:
        table.update_item(
            Key={
                'user_id': _build_extended_id(supply_user),
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


def cancel_booking(supply_user: User, message_id: str):
    table = _get_message_table()

    table.update_item(
        Key={
            'user_id': _build_extended_id(supply_user),
            'id': message_id,
        },
        UpdateExpression="REMOVE demand_user_id"
    )


_STATE_TABLE = 'food-state'
_MESSAGE_TABLE = 'food-message'


def _get_db():
    # if STAGE != 'local':
    #     return boto3.resource('dynamodb', region_name='eu-central-1')

    return boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='eu-central-1',
        aws_access_key_id='any',
        aws_secret_access_key = 'thing',
    )


def _get_state_table():
    """
    `identifier` is a `provider-workflow-user_id` string.
    """
    if is_aws:
        return boto3.resource(
            'dynamodb',
            region_name='eu-central-1',
        ).Table(_STATE_TABLE)

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
    if is_aws:
        return boto3.resource(
            'dynamodb',
            region_name='eu-central-1',
        ).Table(_MESSAGE_TABLE)

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
