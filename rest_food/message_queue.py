import json
import logging
import multiprocessing
from dataclasses import asdict
from typing import Tuple, List, Iterable
from threading import Thread
from uuid import uuid4

import boto3
from telegram import Message as TgMessage

from rest_food.entities import Workflow, Reply
from rest_food.translation import LazyAwareJsonEncoder
from rest_food.settings import STAGE
from rest_food._sync_communication import send_messages


logger = logging.getLogger(__name__)


class BaseMassMessageQueue:
    super_batch_size = None     # type: int

    def put_mass_messages_into_queue(self, items: List[str]):
        raise NotImplementedError()

    def serialize(self, message: Reply, chat_id: int, workflow: Workflow) -> str:
        return json.dumps({
            'reply': asdict(message),
            'chat_id': int(chat_id),
            'workflow': workflow.value,
        }, cls=LazyAwareJsonEncoder)

    def process(self, serialized_data: str):
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


class BaseSingleMessageQueue:
    def put(
        self,
        *,
        tg_chat_id: int,
        original_message: TgMessage = None,
        replies: Iterable[Reply],
        workflow: Workflow
    ):
        replies_data = [asdict(r) for r in replies if r is not None]
        for r in replies_data:
            r.pop('next_state')

        self._put_serialized(json.dumps({
            'tg_chat_id': tg_chat_id,
            'original_message': original_message and original_message.to_dict(),
            'replies': replies_data,
            'workflow': workflow.value,
        }, cls=LazyAwareJsonEncoder))

    def _put_serialized(self, data: str):
        raise NotImplementedError()

    def process(self, data: str):
        try:
            data = json.loads(data)
            send_messages(
                tg_chat_id=data['tg_chat_id'],
                original_message=(
                    data['original_message'] and TgMessage.de_json(data['original_message'], None)
                ),
                replies=[Reply(**x) for x in data['replies']],
                workflow=Workflow(data['workflow']),
            )
        except Exception:
            logger.exception('Message was not sent. Data:\n%s', data)


class AwsMassMessageQueue(BaseMassMessageQueue):
    batch_size = 10
    super_batch_size = 100

    def __init__(self):
        sqs = boto3.resource('sqs', region_name='eu-central-1')
        self._queue = sqs.get_queue_by_name(QueueName=f'send_message_{STAGE}.fifo')
        self._super_queue = sqs.get_queue_by_name(QueueName=f'super_send_{STAGE}.fifo')

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
            MessageDeduplicationId=str(uuid4()),
            MessageGroupId='CommonGroup',
        )

    def redestrib_super_batch(self, items: List[str]):
        for i in range(0, len(items), self.batch_size):
            self.put_mass_messages_into_queue(items[i:i + self.batch_size])

            logger.info('%s messages are sent into send-message queue', i + self.batch_size)

    def put_mass_messages_into_queue(self, items: List[str]):
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
            'MessageDeduplicationId': str(uuid4()),
        } for i, x in enumerate(items)])


class AwsSingleMessageQueue(BaseSingleMessageQueue):
    queue_name = f'single_message_{STAGE}.fifo'

    def __init__(self):
        sqs = boto3.resource('sqs', region_name='eu-central-1')
        self._queue = sqs.get_queue_by_name(QueueName=self.queue_name)

    def _put_serialized(self, data: str):
        send_result = self._queue.send_message(
            MessageBody=data,
            MessageDeduplicationId=str(uuid4()),
            MessageGroupId='CommonGroup',
        )
        logger.info(
            'Message is put into %s with MessageId %s',
            self.queue_name, send_result.get('MessageId')
        )


class LocalQueue:
    def __init__(self, handler):
        self._queue = multiprocessing.Queue()
        self._handler = handler
        multiprocessing.Process(target=self._launch_threads).start()

    def _launch_threads(self):
        ts = [Thread(target=self.read_queue) for _ in range(10)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()

    def read_queue(self):
        while True:
            try:
                msg = self._queue.get()
            except KeyboardInterrupt:
                logger.info('Stop sending messages.')
                break

            self._handler(msg)

    def put(self, msg: str):
        self._queue.put(msg)


class LocalMassMessageQueue(BaseMassMessageQueue):
    super_batch_size = 100

    def __init__(self):
        self._mass_message_queue = LocalQueue(self.process)

    def put_super_batch_into_queue(self, items: List[str]):
        self.put_mass_messages_into_queue(items)

    def put_mass_messages_into_queue(self, items: List[str]):
        for x in items:
            self._mass_message_queue.put(x)


class LocalSingleMessageQueue(BaseSingleMessageQueue):
    def __init__(self):
        self._queue = LocalQueue(self.process)

    def _put_serialized(self, data: str):
        self._queue.put(data)


def _get_mass_queue() -> BaseMassMessageQueue:
    if STAGE in ('live', 'staging'):
        return AwsMassMessageQueue()

    return LocalMassMessageQueue()


def _get_single_queue() -> BaseSingleMessageQueue:
    if STAGE in ('live', 'staging'):
        return AwsSingleMessageQueue()

    return LocalSingleMessageQueue()


_mass_queue = None
_single_queue = None


def get_mass_queue() -> BaseMassMessageQueue:
    global _mass_queue
    if _mass_queue is None:
        _mass_queue = _get_mass_queue()
    return _mass_queue


def get_single_queue() -> BaseSingleMessageQueue:
    global _single_queue
    if _single_queue is None:
        _single_queue = _get_single_queue()
    return _single_queue
