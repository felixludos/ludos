import json
import http
import os
import random
import sys
import time
from collections import OrderedDict, namedtuple
from itertools import chain, product
from string import Formatter
import numpy as np
import argparse
from flask import Flask, render_template, request, send_from_directory
from flask_cors import CORS

import examples
import gsm
from gsm import jsonify
from gsm.io.transmit import LstConverter, create_dir


SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')


null = http.HTTPStatus.NO_CONTENT

#region FRONT routes
app = Flask(__name__, static_folder='static')
app.url_map.converters['lst'] = LstConverter
CORS(app)

def _fmt_output(data):
	return json.dumps(data)

# Meta Host

H = None

@app.route('/restart')
@app.route('/restart/<int:debug>')
def _hard_restart(address=None, debug=False, **settings):
	global H
	
	if address is None:
		assert H is not None, 'must provide an address if no host is running'
		address = H.address
	
	debug = bool(debug)
	
	H = gsm.Host(address, debug=debug, **settings)
	return 'Host restarted (debug={})'.format(debug)

@app.route('/cheat')
@app.route('/cheat/<code>')
def _cheat(code=None):
	return H.cheat(code)

# Game Info and Selection

@app.route('/game/info')
@app.route('/game/info/<name>')
def _get_game_info(name=None):
	return _fmt_output(H.get_game_info(name))

@app.route('/game/available')
def _get_available_games():
	return _fmt_output(H.get_available_games())

@app.route('/game/select/<name>')
def _set_game(name):
	H.set_game(name)
	return 'Game set to: {}'.format(name)

@app.route('/game/players')
def _get_available_players():
	return _fmt_output(H.get_available_players())

@app.route('/setting/<key>/<value>')
def _setting(key, value):
	H.set_setting(key, value)
	return 'Set {}: {}'.format(key, value)
	
@app.route('/del/setting/<key>')
def _del_setting(key):
	H.del_setting(key)
	return 'Del {}'.format(key)

# Managing clients

@app.route('/add/client/<interface>/<lst:users>', methods=['POST']) # post data are the interface settings
@app.route('/add/client/<lst:users>', methods=['POST']) # post data is the passive frontend address
def _add_passive_client(users, interface=None):
	
	address = request.get_json(force=True) if interface is None else None
	settings = {} if interface is None else request.get_json(force=True)
	
	H.add_passive_client(*users, address=address, interface=interface, settings=settings)
	
	out = 'Using {} for: {}'.format(address, ', '.join(users)) if address is not None else \
		'Created an interface ({}) for: {}'.format(interface, ', '.join(users))
	
	return out

@app.route('/ping/clients')
def _ping_clients():
	return H.ping_interfaces()

# Adding Players, Spectators, and Advisors

@app.route('/add/player/<user>/<player>')
def _add_player(user, player):
	return H.add_player(user, player)
	

@app.route('/add/spectator/<user>')
def _add_spectator(user):
	H.add_spectator(user)
	return '{} has joined as a spectator'.format(user)

@app.route('/add/advisor/<user>/<player>')
def _add_advisor(user, player):
	H.add_spectator(user, player)
	return '{} has joined as an advisor for {}'.format(user, player)

# Game Management

@app.route('/begin')
@app.route('/begin/<int:seed>')
def _begin_game(seed=None):
	H.begin_game(seed)
	return '{} has started'.format(H.info['name'])

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
	
	return 'game {} saved'.format(name)
	
@app.route('/load/<name>')
def _load(name):
	
	if H.game is None:
		raise Exception('No game selected')
	
	filename = '{}.gsm'.format(name)
	filedir = os.path.join(SAVE_PATH, H.info['short_name'])
	
	if H.info['short_name'] not in os.listdir(SAVE_PATH):
		return
	
	H.load_game(os.path.join(filedir, filename))
	
	return 'game {} loaded'.format(name)

# In-game Operations

@app.route('/autopause')
def _toggle_autopause():
	return H.toggle_pause()

@app.route('/continue')
@app.route('/continue/<user>')
def _continue(user=None):
	return H.continue_step(user)

@app.route('/action/<user>/<key>/<group>/<lst:action>')
def _action(user, key, group, action):
	return H.take_action(user, group, action, key)

@app.route('/advise/<user>/<group>/<lst:action>')
def _advise(user, group, action):
	return H.give_advice(user, group, action)

@app.route('/status/<user>')
def _get_status(user):
	return H.get_status(user)

@app.route('/log/<user>')
def _get_log(user):
	return H.get_log(user)

def main(argv=None):
	parser = argparse.ArgumentParser(description='Start the host server.')
	
	parser.add_argument('--host', default='localhost', type=str,
	                    help='host for the backend')
	parser.add_argument('--port', default=5000, type=int,
	                    help='port for the backend')
	
	parser.add_argument('--settings', type=str, default='{}',
	                    help='optional args for interface, specified as a json str (of a dict with kwargs)')
	
	args = parser.parse_args(argv)
	
	address = 'http://{}:{}/'.format(args.host, args.port)
	settings = json.loads(args.settings)
	
	_hard_restart(address, **settings)
	
	app.run(host=args.host, port=args.port)
	
	

if __name__ == "__main__":
	main()
	
	