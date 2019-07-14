from flask import Flask, request
from rest_food.handlers import tg_supply, tg_demand


app = Flask(__name__)


@app.route('/tg/supply/path-key/', methods=['POST'])
def flask_tg_supply():
    tg_supply(request.get_json())
    return '', 200


@app.route('/tg/demand/path-key/', methods=['POST'])
def flask_tg_demand():
    tg_demand(request.get_json())
    return '', 200



if __name__ == '__main__':
    app.run()