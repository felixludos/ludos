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

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')

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

def create_dir(path):
	try:
		os.mkdir(path)
	except OSError as e:
		raise e

#endregion

null = http.HTTPStatus.NO_CONTENT

#region FRONT routes
app = Flask(__name__, static_folder='static')
app.url_map.converters['lst'] = LstConverter
CORS(app)

def _fmt_output(data):
	return json.dumps(data)

# Meta Host

@app.route('/restart')
def _hard_restart():
	global H
	H = gsm.Host()
	return null

# Game Info and Selection

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

@app.route('/setting/<key>/<value>')
def _setting(key, value):
	H.set_setting(key, value)
	
@app.route('/del_setting/<key>')
def _del_setting(key):
	H.del_setting(key)

# Managing clients

@app.route('/add_passive_client/<lst:users>/<path:address>')
def _add_passive_client(users, address):
	H.add_passive_client(address, *users)
	return null



# Adding Players, Spectators, and Advisors

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

# Game Management

@app.route('/begin')
def _begin_game():
	H.begin_game()
	return null

@app.route('/save/<name>')
@app.route('/save/<name>/<overwrite>')
def _save(name, overwrite='false'):
	
	if H.game is None:
		raise Exception('No game selected')
	
	filename = '{}.gsm'.format(name)
	filedir = os.path.join(SAVE_PATH, H.info['short_name'])
	
	if H.info['short_name'] not in os.listdir(SAVE_PATH):
		create_dir(filedir)
	
	if overwrite != 'true' and filename in os.listdir(filedir):
		raise Exception('This savefile already exists')
	
	H.save_game(os.path.join(filedir, filename))
	
@app.route('/load/<name>')
def _load(name):
	
	if H.game is None:
		raise Exception('No game selected')
	
	filename = '{}.gsm'.format(name)
	filedir = os.path.join(SAVE_PATH, H.info['short_name'])
	
	if H.info['short_name'] not in os.listdir(SAVE_PATH):
		return
	
	H.load_game(os.path.join(filedir, filename))

# In-game Operations

@app.route('/action/<user>/<key>/<lst:action>')
def _action(user, key, action):
	return H.take_action(user, action, key)

@app.route('/status/<user>')
def _get_status(user):
	return H.get_status(user)



if __name__ == "__main__":
	_hard_restart()
	
	app.run(host='localhost', port=5000)