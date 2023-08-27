import datetime
import logging
from typing import Optional, Union, List

from bson.objectid import ObjectId
from pymongo import MongoClient, ReturnDocument

from rest_food.entities import User, Message, Command, DT_FORMAT
from rest_food.enums import Provider, Workflow, UserInfoField
from rest_food.settings import DB_CONNECTION_STRING, DB_NAME, ADMIN_USERNAMES


logger = logging.getLogger(__name__)


def create_mongo_connector():
    return MongoClient(DB_CONNECTION_STRING)[DB_NAME]


db = create_mongo_connector()


def import_users(data: List[dict]):
    db.users.insert(data)


def import_messages(data: List[dict]):
    db.messages.insert(data)


def _update_user(
        user_id: Union[str, int], provider: Provider, workflow: Workflow, *, method: str='$set', update: dict,
) -> dict:
    return db.users.find_one_and_update(
        {
            'user_id': str(user_id),
            'provider': provider.value,
            'workflow': workflow.value,
        },
        {method: update},
        return_document=ReturnDocument.AFTER,
    )


def _update_user_entity(user: User, update: dict, *, method: str='$set') -> User:
    updated_doc = _update_user(user.user_id, user.provider, user.workflow, update=update, method=method)
    return User.from_dict(updated_doc)


def _update_message(message_id: str, *, owner_id: Optional[str]=None, update: dict):
    find = {
        '_id': ObjectId(message_id),
    }
    if owner_id:
        find['owner_id'] = owner_id

    db.messages.update_one(find, {'$set': update})


def _build_extended_id(user: User) -> str:
    return f'{user.provider.value}|{user.user_id}'


def get_user_by_id(db_id: str) -> User:
    record = db.users.find_one({
        '_id': ObjectId(db_id),
    })
    return record and User.from_dict(record)


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
    """
    Queries db for a user record with user_id, provider and workflow specified.
        Marks it as active if found but not active. Creates a new active one if no record found.
    """
    user = get_user(user_id, provider, workflow)

    if user is None:
        # Create user.

        info = info or {}
        info[UserInfoField.DISPLAY_USERNAME.value] = True
        user = User(
            user_id=user_id,
            chat_id=chat_id,
            info=info,
            is_active=True,
            provider=provider,
            workflow=workflow,
        )
        user._id = str(_create_user(user))

    else:
        # Update user.

        update_statement = {}

        # username if changed.
        if info.get(UserInfoField.USERNAME.value) != user.info.get(UserInfoField.USERNAME.value):
            update_statement[f'info.{UserInfoField.USERNAME.value}'] = info.get(UserInfoField.USERNAME.value)

        # `language` if changed and allowed.
        if info.get(UserInfoField.LANGUAGE.value) != user.info.get(UserInfoField.LANGUAGE.value):
            if not user.info.get(UserInfoField.IS_APPROVED_LANGUAGE.value):
                update_statement[f'info.{UserInfoField.LANGUAGE.value}'] = info[UserInfoField.LANGUAGE.value]
                if UserInfoField.IS_APPROVED_LANGUAGE.value not in user.info:
                    update_statement[f'info.{UserInfoField.IS_APPROVED_LANGUAGE.value}'] = False

        # `is_active` if it was not active before.
        if not user.is_active:
            update_statement.update({'is_active': True, 'active_from': datetime.datetime.utcnow()})

        if update_statement:
            user = _update_user_entity(user, update_statement)

    return user


def _create_user(user: User) -> ObjectId:
    create_time = datetime.datetime.utcnow()

    if UserInfoField.LANGUAGE.value in user.info:
        user.info[UserInfoField.IS_APPROVED_LANGUAGE.value] = False

    result = db.users.insert_one({
        'user_id': str(user.user_id),
        'chat_id': user.chat_id,
        'provider': user.provider.value,
        'workflow': user.workflow.value,
        'is_active': user.is_active,
        'info': user.info,
        'context': {},
        'active_from' if user.is_active else 'inactive_from': create_time,
        'created_at': create_time,
    })
    return result.inserted_id


def get_demand_users():
    """

    Returns
    -------
    All active demand users.

    """
    return [
        User.from_dict(x)
        for x in db.users.find({
            'workflow': Workflow.DEMAND.value,
            'is_active': {'$ne': False},
        })
    ]


def get_admin_users():
    return [
        User.from_dict(x)
        for x in db.users.find({
            '$or': [{'is_admin': True}, {'info.username': {'$in': ADMIN_USERNAMES}}],
            'is_active': {'$ne': False},
        })
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


def unset_info(user: User, info_field: UserInfoField):
    _update_user_entity(user, {f'info.{info_field.value}': ''}, method='$unset')

    if info_field.value in user.info:
        del user.info[info_field.value]


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
    db.messages.insert_one({
        '_id': message_id,
        'owner_id': user.id,
        'products': [message],
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


def set_message_time(message_id: str, time_message: str):
    _update_message(
        message_id=message_id, update={'take_time': time_message}
    )


def set_message_publication_time(message_id: str):
    _update_message(
        message_id,
        update={
            'dt_published': datetime.datetime.now().strftime(DT_FORMAT)
        }
    )


def cancel_supply_message(user: User, *, provider: Provider):
    _update_user(user.user_id, provider, Workflow.SUPPLY, update={'editing_message_id': None})
    db.messages.remove({'_id': ObjectId(user.editing_message_id)})
    user.editing_message_id = None


def list_messages(supply_user: User, interval: datetime.timedelta=datetime.timedelta(days=2)):
    dt_from = (datetime.datetime.now() - interval).strftime(DT_FORMAT)

    records = db.messages.find({
        'owner_id': supply_user.id,
        'dt_published': {'$gt': dt_from},
    })

    return [Message.from_db(x) for x in records]


def get_supply_editing_message(user: User) -> Optional[Message]:
    if user.editing_message_id is None:
        return None

    return get_supply_message_record(user=user, message_id=user.editing_message_id)


def get_supply_message_record(*, user, message_id: str) -> Optional[Message]:
    message = get_supply_message_record_by_id(message_id)

    # There is some inconsistency in db which is not investigated yet.
    # Some records had owner_id as str, other had it as ObjectId
    if ObjectId(message.owner_id) != user.id:
        return None

    return message


def get_supply_message_record_by_id(message_id: str) -> Message:
    return Message.from_db(db.messages.find_one({
        '_id': ObjectId(message_id),
    }))


def get_message_demanded_user(*, supply_user, message_id: str) -> Optional[User]:
    message_record = get_supply_message_record(user=supply_user, message_id=message_id)
    if message_record is None or message_record.demand_user_id is None:
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


def set_inactive(chat_id: int, provider: Provider, workflow: Workflow):
    db.users.update_one(
        {
            'chat_id': chat_id,
            'provider': provider.value,
            'workflow': workflow.value,
        },
        {
            '$set': {
                'is_active': False,
                'inactive_from': datetime.datetime.utcnow(),
            },
        }
    )
