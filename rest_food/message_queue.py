import json
import logging
import multiprocessing
from dataclasses import asdict
from typing import Tuple, List
from hashlib import sha256

import boto3


from rest_food.entities import Workflow, Reply
from rest_food.translation import LazyAwareJsonEncoder
from rest_food.settings import STAGE


logger = logging.getLogger(__name__)


class BaseMessageQueue:
    super_batch_size = None     # type: int

    def put_batch_into_queue(self, items: List[str]):
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

    def put_super_batch_into_queue(self, items: List[str]):
        raise NotImplementedError()


    def push_super_batch(self, *, message_and_chat_id: List[Tuple[Reply, int]], workflow: Workflow):
        for i in range(0, len(message_and_chat_id), self.super_batch_size):
            self.put_super_batch_into_queue(
                [
                    self.serialize(msg, chat_id, workflow=workflow)
                    for msg, chat_id in message_and_chat_id[i:i+self.super_batch_size]
                ]
            )
            logger.info('%s messages are sent into super-queue', i+self.super_batch_size)


class AwsMessageQueue(BaseMessageQueue):
    batch_size = 10
    super_batch_size = 100

    def __init__(self):
        logger.info('Before creating sqs service.')
        sqs = boto3.resource('sqs', region_name='eu-central-1')
        logger.info('Before connecting to sqs.')
        self._queue = sqs.get_queue_by_name(QueueName=f'send_message_{STAGE}.fifo')
        logger.info('After connecting to send_message.')
        self._super_queue = sqs.get_queue_by_name(QueueName=f'super_send_{STAGE}.fifo')
        logger.info('After connecting to super_send.')

    def put_super_batch_into_queue(self, items: List[str]):
        """

        Parameters
        ----------
        items
            100 items

        """
        payload = json.dumps(items)
        self._super_queue.send_message(
            MessageBody=payload,
            MessageDeduplicationId=sha256(payload.encode()).hexdigest(),
            MessageGroupId='CommonGroup',
        )

    def redestrib_super_batch(self, items: List[str]):
        for i in range(0, len(items), self.batch_size):
            self.put_batch_into_queue(items[i:i + self.batch_size])

            logger.info('%s messages are sent into send-message queue', i + self.batch_size)

    def put_batch_into_queue(self, items: List[str]):
        """

        Parameters
        ----------
        items
            10 items
        """
        self._queue.send_messages(Entries=[{
            'Id': str(i),
            'MessageBody': x,
            'MessageGroupId': str(i),
            'MessageDeduplicationId': sha256(x.encode()).hexdigest(),
        } for i, x in enumerate(items)])


class LocalMessageQueue(BaseMessageQueue):
    super_batch_size = 100

    def __init__(self):
        self._queue = multiprocessing.Queue()
        multiprocessing.Process(target=self.read_queue).start()

    def put_super_batch_into_queue(self, items: List[str]):
        self.put_batch_into_queue(items)

    def put_batch_into_queue(self, items: List[str]):
        for x in items:
            self._queue.put(x)

    def read_queue(self):
        while True:
            try:
                msg = self._queue.get()
            except KeyboardInterrupt:
                break

            print('Got message')
            self.process(msg)


def _get_queue() -> BaseMessageQueue:
    if STAGE in ('LIVE', 'live', 'staging'):
        return AwsMessageQueue()

    return LocalMessageQueue()


_the_queue = None


def get_queue():
    global _the_queue
    if _the_queue is None:
        _the_queue = _get_queue()
    return _the_queue
