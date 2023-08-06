from flask import Flask, request, jsonify
from flask.json.provider import DefaultJSONProvider
from rest_food.handlers import tg_supply, tg_demand
from rest_food.translation import LazyAwareJsonEncoder
from rest_food.settings import BOT_PATH_KEY

app = Flask(__name__)


@app.route(f'/tg/supply/{BOT_PATH_KEY}/', methods=['POST'])
def flask_tg_supply():
    response = tg_supply(request.get_json()) or {}
    return jsonify(response)


@app.route(f'/tg/demand/{BOT_PATH_KEY}/', methods=['POST'])
def flask_tg_demand():
    response = tg_demand(request.get_json()) or {}
    return jsonify(response)



if __name__ == '__main__':
    app.json.default = LazyAwareJsonEncoder().default
    app.run()
