import json
import http
import os
import random
import sys
import time
from collections import OrderedDict, namedtuple
from itertools import chain, product
from string import Formatter
import gsm
import numpy as np
from flask import Flask, render_template, request, send_from_directory
from flask_cors import CORS
from gsm.util import jsonify

from examples.tictactoe.main import TicTacToe
from app_interface import Game, ymlFile_jString, userSpecYmlPath

from werkzeug.routing import BaseConverter

class LstConverter(BaseConverter):

	def to_python(self, value):
		out = []
		for v in value.split('+'):
			try:
				out.append(int(v))
			except:
				out.append(v)
		return tuple(out)

	def to_url(self, values):
		return '+'.join(BaseConverter.to_url(value)
						for value in values)

#endregion

null = http.HTTPStatus.NO_CONTENT

#region FRONT routes
app = Flask(__name__, static_folder='static')
app.url_map.converters['lst'] = LstConverter
CORS(app)

def _fmt_output(data):
	return json.dumps(data)

@app.route('/get_game_info/<name>')
def _get_game_info(name):
	return _fmt_output(H.get_game_info(name))

@app.route('/get_available_games')
def _get_available_games():
	return _fmt_output(H.get_available_games())

@app.route('/set_game/<name>')
def _set_game(name):
	H.set_game(name)
	return null

@app.route('/add_player/<user>/<player>')
def _add_player(user, player):
	H.add_player(user, player)
	return null

@app.route('/add_spectator/<user>')
def _add_spectator(user):
	H.add_spectator(user)
	return null

@app.route('/add_advisor/<user>/<player>')
def _add_advisor(user, player):
	H.add_spectator(user, player)
	return null

@app.route('/add_passive_client/<lst:users>/<path:address>')
def _add_passive_client(users, address):
	H.add_passive_client(address, *users)
	return null

@app.route('/action/<user>/<key>/<action:action>')
def _action(user, key, action):
	raise NotImplementedError

@app.route('/status/<user>')
def _get_status(user):
	return H.get_status(user)



if __name__ == "__main__":
	H = gsm.Host()
	
	app.run(host='localhost', port=5000)