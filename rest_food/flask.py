from flask import Flask, request, jsonify
from rest_food.handlers import tg_supply, tg_demand
from rest_food.translation import LazyAwareJsonEncoder

app = Flask(__name__)


@app.route('/tg/supply/path-key/', methods=['POST'])
def flask_tg_supply():
    response = tg_supply(request.get_json()) or {}
    return jsonify(response)


@app.route('/tg/demand/path-key/', methods=['POST'])
def flask_tg_demand():
    response = tg_demand(request.get_json()) or {}
    return jsonify(response)



if __name__ == '__main__':
    app.json_encoder = LazyAwareJsonEncoder
    app.run()
