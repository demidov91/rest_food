import json
import logging
import os
from dataclasses import asdict
from typing import Tuple, List

import boto3


from rest_food.entities import Workflow, Reply
from rest_food.translation import LazyAwareJsonEncoder


logger = logging.getLogger(__name__)


class BaseMessageQueue:
    batch_size = None   # type: int

    def put_batch_into_queue(self, data: List[str]):
        raise NotImplementedError()

    def deserialize(self, queue_entry: dict) -> dict:
        raise NotImplementedError()

    def serialize(self, message: Reply, chat_id: int, workflow: Workflow) -> str:
        return json.dumps({
            'reply': asdict(message),
            'chat_id': int(chat_id),
            'workflow': workflow.value,
        }, cls=LazyAwareJsonEncoder)

    def process(self, queue_entry: dict):
        from rest_food.communication import send_messages

        data = self.deserialize(queue_entry)
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
        sqs = boto3.resource('sqs', region_name='eu-central-1')
        self._queue = sqs.get_queue_by_name(QueueName='send_message.live')

    def put_batch_into_queue(self, data: List[str]):
        self._queue.send_messages([{
            'Id': i,
            'MessageBody': x,
        } for i, x in enumerate(data)])

    def deserialize(self, queue_entry: dict) -> dict:
        pass


class LocalMessageQueue(BaseMessageQueue):
    """
    This is to be implemented with process queue for the flask mode.
    """
    batch_size = 1

    def put_batch_into_queue(self, data: List[str]):
        for x in data:
            self.process({'data': x})

    def deserialize(self, queue_entry: dict) -> dict:
        return json.loads(queue_entry['data'])


def _get_queue() -> BaseMessageQueue:
    if os.environ.get('STAGE') == 'LIVE':
        return AwsMessageQueue()

    return LocalMessageQueue()


message_queue = _get_queue()
