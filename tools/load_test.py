import time
from threading import Thread

from matplotlib import pyplot as plt
from pymongo import MongoClient

from rest_food.settings import DB_CONNECTION_STRING, DB_NAME
from rest_food.db import get_demand_users, db as sync_db
import random
import json
from uuid import uuid4


stats = []


class LoadClient:
    parallelism = 100
    iterations_count = 50

    user_ids = None     # type: list
    message_ids = None  # type: list

    def run(self, user_ids, message_ids, is_async=True):
        self.user_ids = user_ids
        self.message_ids = message_ids

        start = time.time_ns()

        self._launch_sync()

        print('Total: %s' % ((time.time_ns() - start) // 10**6))

    def _worker(self):


        db = MongoClient(DB_CONNECTION_STRING)[DB_NAME]

        for i in range(self.iterations_count):
            start = time.time_ns()

            doc = db.users.find_one({
                'user_id': random.choice(self.user_ids),
                'workflow': 'demand',
                'provider': 'telegram',
            })

            after_user_read = time.time_ns()

            assert doc is not None


            doc = db.messages.find_one({
                '_id': random.choice(self.message_ids),
            })
            assert doc is not None

            after_message_read = time.time_ns()

            update_result = db.users.update_one({
                'user_id': random.choice(self.user_ids),
                'workflow': 'demand',
                'provider': 'telegram',
            }, {
                '$set': {
                    'info.test_field': str(uuid4()),
                }
            })
            assert update_result.modified_count == 1

            after_user_update = time.time_ns()

            stats.append({
                'read_users': (after_user_read - start) // 10**6,
                'read_messages': (after_message_read - after_user_read) // 10**6,
                'write_users': (after_user_update - after_message_read) // 10**6,
            })

        print('Done')

    def _launch_sync(self):
        ts = [Thread(target=self._worker) for _ in range(self.parallelism)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()


def run():
    user_id_collection = [x.user_id for x in get_demand_users()]
    message_id_collection = [x['_id'] for x in sync_db.messages.find({})]

    LoadClient().run(**{
        'user_ids': user_id_collection,
        'message_ids': message_id_collection,
        'is_async': False,
    })

    with open('stats.json', mode='wt') as f:
        json.dump(stats, f)


def draw_stats():
    with open('stats.json', mode='rt') as f:
        data = json.load(f)

    plt.plot(tuple(range(len(data))), [x['read_users'] for x in data], 'o')
    plt.show()

    plt.plot(tuple(range(len(data))), [x['read_messages'] for x in data], 'o')
    plt.show()

    plt.plot(tuple(range(len(data))), [x['write_users'] for x in data], 'o')
    plt.show()


if __name__ == '__main__':
    run()
    draw_stats()
