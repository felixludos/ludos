import json
import os
import random
import sys
import time
import socket
import argparse
from collections import OrderedDict, namedtuple
from itertools import chain, product
from string import Formatter

import gsm

import numpy as np
from flask import Flask, render_template, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
# app.url_map.converters['action'] = ActionConverter
CORS(app)

I = None

def _fmt_request():
	try:
		return request.get_json(force=True)
	except:
		return json.loads(json.loads(request.data))

@app.route('/step/<user>', methods=['POST'])
def step(user, data=None):
	if data is None:
		data = _fmt_request()
	return I.step(user, data)

@app.route('/player/<user>/<player>')
def set_player(user, player):
	I.set_player(user, player)
	return '{}'

@app.route('/ping')
def ping():
	return I.ping()


@app.route('/reset/<user>')
def reset(user):
	return I.reset(user)

@app.route('/save')
def save():
	return I.save()

@app.route('/load', methods=['POST'])
def load(data=None):
	if data is None:
		data = _fmt_request()
	return I.load(data)

def main(argv=None):
	parser = argparse.ArgumentParser(description='Start a passive frontend.')
	parser.add_argument('interface', type=str, default=None,
	                    help='Name of registered interface')
	
	parser.add_argument('--settings', type=str, default='{}',
	                    help='optional args for interface, specified as a json str (of a dict with kwargs)')
	parser.add_argument('--user', default=None, type=str,
	                    help='name of user (default: <interface.name>:<port>)')
	
	parser.add_argument('--port', default=5000, type=int,
	                    help='port for this frontend')
	parser.add_argument('--auto-find', action='store_true',
	                    help='find open port if current doesn\'t work.')
	# args = parser.parse_args(['agent', '--settings', '{"agent_type":"random"}', '--auto-find'])
	args = parser.parse_args(argv)
	
	port = args.port
	is_available = False
	
	if args.auto_find:
		while not is_available:
			is_available = True
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.bind(('localhost', port))
				port = sock.getsockname()[1]
				sock.close()
			except OSError:
				is_available = False
				port += 1
	
	global I
	I = gsm.get_interface(args.interface)(**json.loads(args.settings))
	
	print(I.get_type())
	
	app.run(host='localhost', port=port)

if __name__ == "__main__":
	main()