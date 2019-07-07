import boto3
from botocore.exceptions import ClientError

from rest_food.entities import Provider, Workflow, User


def _build_identifier(user_id, provider: Provider, workflow: Workflow):
    return f'{provider.value}-{workflow.value}-{user_id}'


def get_user(user_id, provider: Provider, workflow: Workflow) -> User:
    table = _get_state_table()
    response = table.get_item(
        Key={'id': _build_identifier(user_id, provider, workflow)},
        ConsistentRead=True,
    )

    if 'Item' not in response:
        user = User(user_id=user_id, provider=provider, workflow=workflow)
        user.id = _create_user(user)
        return user

    data = response['Item']

    return User(
        id=data['id'],
        user_id=data['user_id'],
        state=data.get('state'),
        info=data.get('info'),
        provider=provider,
        workflow=workflow,
    )


def _create_user(user: User):
    table = _get_state_table()
    identifier = _build_identifier(user.user_id, user.provider, user.workflow)
    table.put_item(Item={
        'id': identifier,
        'user_id': user.user_id,
        'info': {
            'address': 'Minsk, Charužaj, 22',
            'time_to_visit': 'till 23:00',
        },
    })
    return identifier


def get_supply_user(tg_user_id: int):
    user = get_user(tg_user_id, Provider.TG, Workflow.SUPPLY)
    if not user.info:
        return None

    return user


def extend_supply_message():
    pass


def publish_supply():
    pass


_STATE_TABLE = 'food-state'

def _get_state_table():
    """
    `identifier` is a `provider-workflow-user_id` string.
    """
    # if STAGE != 'local':
    #     return boto3.resource('dynamodb', region_name='eu-central-1').Table(_STATE_TABLE)

    db = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='eu-central-1'
    )

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