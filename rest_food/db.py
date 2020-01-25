import datetime
import logging
from typing import Optional, Union

from bson.objectid import ObjectId
from pymongo import MongoClient

from rest_food.entities import Provider, Workflow, User, Message, UserInfoField, Command, DT_FORMAT
from rest_food.settings import DB_CONNECTION_STRING, DB_NAME


logger = logging.getLogger(__name__)
db = MongoClient(DB_CONNECTION_STRING)[DB_NAME]


def _update_user(user_id: Union[str, int], provider: Provider, workflow: Workflow, *, update: dict):
    db.users.update_one({
        'user_id': str(user_id),
        'provider': provider.value,
        'workflow': workflow.value,

    }, {
        '$set': update,
    })


def _update_user_entity(user: User, update: dict):
    _update_user(user.user_id, user.provider, user.workflow, update=update)


def _update_message(message_id: str, *, owner_id: Optional[str], update: dict):
    find = {
        '_id': ObjectId(message_id),
    }
    if owner_id:
        find['owner_id'] = owner_id

    db.messages.update_one(find, {'$set': update})


def _build_extended_id(user: User) -> str:
    return f'{user.provider.value}|{user.user_id}'


def get_user(user_id, provider: Provider, workflow: Workflow) -> Optional[User]:
    record = db.users.find_one({
        'user_id': str(user_id),
        'provider': provider.value,
        'workflow': workflow.value,
    })

    return record and User.from_dict(record)


def get_supply_user(user_id: str, provider: Provider) -> User:
    return get_user(user_id, provider, workflow=Workflow.SUPPLY)


def get_demand_user(user_id: str, provider: Provider) -> User:
    return get_user(user_id, provider, workflow=Workflow.DEMAND)


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
    db.users.insert_one({
        'user_id': str(user.user_id),
        'chat_id': user.chat_id,
        'provider': provider.value,
        'workflow': workflow.value,
        'info': user.info,
        'context': {},
    })


def get_demand_users():
    return [
        User.from_dict(x)
        for x in db.users.find({'workflow': Workflow.DEMAND.value})
    ]


def set_state(*, user_id: str, provider: Provider, workflow: Workflow, state: str):
    _update_user(user_id, provider, workflow, update={
        'bot_state': state,
    })


def set_info(user: User, info_field: UserInfoField, data):
    _update_user_entity(user, {
        f'info.{info_field.value}': data
    })

    user.info[info_field.value] = data


def set_next_command(user: User, command: Command):
    _update_user_entity(user, {
        'context.next_command': command.name,
        'context.arguments': command.arguments,
    })

    user.context['next_command'] = command.name
    user.context['arguments'] = command.arguments


def set_booking_to_cancel(user: User, message_id: str):
    _update_user_entity(user, {
        'context.booking_to_cancel': message_id,
    })

    user.context['booking_to_cancel'] = message_id


def create_supply_message(user: User, message: str, *, provider: Provider):
    message_id = ObjectId()
    dt_created = datetime.datetime.now().strftime(DT_FORMAT)
    db.messages.insert_one({
        '_id': message_id,
        'owner_id': user.id,
        'products': [message],
        'dt_created': dt_created,
    })

    _update_user(
        user.user_id, provider, Workflow.SUPPLY, update={'editing_message_id': str(message_id)}
    )

    user.editing_message_id = message_id
    return message_id


def extend_supply_message(user: User, message: str):
    db.messages.update({
        '_id': ObjectId(user.editing_message_id),
        'owner_id': user.id,
    }, {
        '$push': {'products': message},
    })


def set_supply_message_time(user: User, time_message: str):
    _update_message(
        message_id=user.editing_message_id, owner_id=user.id, update={'take_time': time_message}
    )


def cancel_supply_message(user: User, *, provider:Provider):
    result = db.users.update_one(
        {
            'user_id': str(user.user_id),
            'provider': provider.value,
            'workflow': Workflow.SUPPLY.value,
        },
        {
            'editing_message_id': None,
        }
    )

    if result['modified_count'] != 1:
        logger.error('Supply message was not cancelled. Update result: %s', result)

    user.editing_message_id = None


def list_messages(supply_user: User, interval: datetime.timedelta=datetime.timedelta(days=2)):
    dt_from = (datetime.datetime.now() - interval).strftime(DT_FORMAT)

    records = db.messages.find({
        'owner_id': supply_user.id,
        'dt_created': {'$gt': dt_from},
    })

    return [Message.from_db(x) for x in records]


def get_supply_editing_message(user: User) -> Optional[Message]:
    if user.editing_message_id is None:
        return None

    return get_supply_message_record(user=user, message_id=user.editing_message_id)


def get_supply_message_record(*, user, message_id: str) -> Message:
    return Message.from_db(db.messages.find_one({
        '_id': ObjectId(message_id),
        'owner_id': user.id,
    }))


def get_message_demanded_user(*, supply_user, message_id: str) -> Optional[User]:
    message_record = get_supply_message_record(user=supply_user, message_id=message_id)
    if message_record.demand_user_id is None:
        return None

    provider, user_id = message_record.demand_user_id.split('|')
    return get_user(user_id=user_id, provider=Provider(provider), workflow=Workflow.DEMAND)


def mark_message_as_booked(demand_user: User, message_id: str):
    extended_id = _build_extended_id(demand_user)

    result = db.messages.update_one({
        '_id': ObjectId(message_id),
        'demand_user_id': None,
    }, {
        '$set': {'demand_user_id': extended_id},
    })

    return result.modified_count > 0


def cancel_booking(supply_user: User, message_id: str):
    _update_message(message_id, owner_id=supply_user.id, update={'demand_user_id': None})
