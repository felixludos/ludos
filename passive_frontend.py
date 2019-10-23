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
def _step(user):
	if request.method == 'POST':
		data = _fmt_request()
		return I.step(user, data)
	else:
		raise Exception('Unknown call - must call step with post')


@app.route('/ping')
def _ping():
	return I.ping()


@app.route('/reset/<user>')
def _reset(user):
	return I.reset(user)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Start a passive frontend.')
	parser.add_argument('interface', type=str, default=None,
	                    help='Name of registered interface')
	parser.add_argument('--user', default=None, type=str,
	                    help='name of user (default: <interface.name>:<port>)')
	parser.add_argument('--port', default=5000, type=int,
	                    help='port for this frontend')
	parser.add_argument('--auto-find', action='store_true',
	                    help='find open port if current doesn\'t work.')
	args = parser.parse_args()
	
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
	
	I = gsm.get_interface(args.interface)()
	
	print(I.name)
	
	app.run(host='localhost', port=port)