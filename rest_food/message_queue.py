import json
import logging
import os
from dataclasses import asdict
from typing import Tuple, List
from uuid import uuid4

import boto3


from rest_food.entities import Workflow, Reply
from rest_food.translation import LazyAwareJsonEncoder


logger = logging.getLogger(__name__)


# It's declared here to prevent future merge conflict in settings.py
stage = os.environ.get('STAGE')


class BaseMessageQueue:
    batch_size = None   # type: int

    def put_batch_into_queue(self, data: List[str]):
        raise NotImplementedError()

    def serialize(self, message: Reply, chat_id: int, workflow: Workflow) -> str:
        return json.dumps({
            'reply': asdict(message),
            'chat_id': int(chat_id),
            'workflow': workflow.value,
        }, cls=LazyAwareJsonEncoder)

    def process(self, serialized_data: str):
        from rest_food.communication import send_messages

        data = json.loads(serialized_data)
        try:
            send_messages(
                tg_chat_id=data['chat_id'],
                replies=[Reply(**data['reply'])],
                workflow=Workflow(data['workflow'])
            )
        except Exception as e:
            logger.exception('Message was not send:\n%s', data)

    def push_many(self, *, message_and_chat_id: List[Tuple[Reply, int]], workflow: Workflow):
        for i in range(0, len(message_and_chat_id), self.batch_size):
            self.put_batch_into_queue(
                [
                    self.serialize(msg, chat_id, workflow=workflow)
                    for msg, chat_id in message_and_chat_id[i:i+self.batch_size]
                ]
            )


class AwsMessageQueue(BaseMessageQueue):
    batch_size = 10

    def __init__(self):
        logger.info('Before creating sqs service.')
        sqs = boto3.resource('sqs', region_name='eu-central-1')
        logger.info('Before connecting to sqs.')
        self._queue = sqs.get_queue_by_name(QueueName=f'send_message_{stage}.fifo')
        logger.info('After connecting to sqs.')

    def put_batch_into_queue(self, data: List[str]):
        self._queue.send_messages(Entries=[{
            'Id': str(i),
            'MessageBody': x,
            'MessageGroupId': str(i),
            'MessageDeduplicationId': str(uuid4()),
        } for i, x in enumerate(data)])


class LocalMessageQueue(BaseMessageQueue):
    """
    This is to be implemented with process queue for the flask mode.
    """
    batch_size = 1

    def put_batch_into_queue(self, data: List[str]):
        for x in data:
            self.process(x)


def _get_queue() -> BaseMessageQueue:
    if stage in ('LIVE', 'live', 'staging'):
        return AwsMessageQueue()

    return LocalMessageQueue()


message_queue = _get_queue()
