import argparse
import json
from decimal import Decimal

from rest_food.db import import_messages, import_users


argparser = argparse.ArgumentParser(
    description='Reformat dynamodb users data fetched with `export-dynamodb` '
                'into mongodb compatible format'
)
argparser.add_argument(
    '-i',
    dest='in_file',
    default=None,
    help='input file'
)
argparser.add_argument(
    '-o',
    dest='out_file',
    default=None,
    help='output file'
)
argparser.add_argument('command', choices=['users', 'messages', 'load_users', 'load_messages'])


class DecimalAware(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)

        return super().default(o)


def _convert_users(in_filename: str, out_filename: str):
    in_filename = in_filename or 'local_data/users.json'
    out_filename = out_filename or 'local_data/mongo_users.json'

    with open(in_filename, mode='rt') as f:
        data = json.load(f)

    outdata = []

    for item in data:
        converted = {}
        for key in item:
            if key in ('workflow', 'user_id', 'provider'):
                converted[key] = item[key]
            elif key == 'chat_id':
                converted[key] = int(item[key])
            elif key == 'bot_state':
                converted[key] = item[key] if item[key] != 'None' else None
            elif key in ('info', 'context'):
                converted[key] = eval(item[key])
            elif key in ('cluster', 'editing_message_id'):
                pass
            else:
                raise ValueError(key)

        outdata.append(converted)

    with open(out_filename, mode='wt') as f:
        json.dump(outdata, f, indent=2, ensure_ascii=False, cls=DecimalAware)


def _convert_messages(in_filename: str, out_filename: str):
    in_filename = in_filename or 'local_data/messages.json'
    out_filename = out_filename or 'local_data/mongo_messages.json'

    with open(in_filename, mode='rt') as f:
        data = json.load(f)

    outdata = []

    for item in data:
        if 'take_time' not in item:
            continue

        converted = {}

        for key in item:
            if key in ('user_id', 'demand_user_id', 'dt_published', 'take_time'):
                converted[key] = item[key]
            elif key == 'products':
                converted[key] = eval(item[key])
            elif key in ('id', ):
                pass
            else:
                raise ValueError(key)

        outdata.append(converted)

    with open(out_filename, mode='wt') as f:
        json.dump(outdata, f, indent=2, ensure_ascii=False)


def _load_users(filename: str):
    filename = filename or 'local_data/mongo_users.json'
    with open(filename, mode='rt') as f:
        data = json.load(f)

    import_users(data)


def _load_messages(filename: str):
    filename = filename or 'local_data/mongo_messages.json'
    with open(filename, mode='rt') as f:
        data = json.load(f)

    import_messages(data)


def run():
    args = argparser.parse_args()

    if args.command == 'users':
        _convert_users(args.in_file, args.out_file)
    elif args.command == 'messages':
        _convert_messages(args.in_file, args.out_file)
    elif args.command == 'load_users':
        _load_users(args.in_file)
    elif args.command == 'load_messages':
        _load_messages(args.in_file)



if __name__ == '__main__':
    run()
