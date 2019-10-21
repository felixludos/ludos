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

@app.route('/step', methods=['POST'])
@app.route('/step/', methods=['POST'])
def _step():
	if request.method == 'POST':
		data = request.form
		I.step(data)
	else:
		raise Exception('Unknown call - must call step with post')


@app.route('/ping')
@app.route('/ping/')
def _ping():
	return I.ping()


@app.route('/reset')
@app.route('/reset/')
def _reset():
	return I.reset()



if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Start a passive frontend.')
	parser.add_argument('interface', type=str, default=None,
	                    help='Name of registered interface')
	parser.add_argument('--port', default=5000, type=int,
	                    help='sum the integers (default: find the max)')
	args = parser.parse_args()
	
	port = args.port
	is_available = False
	
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
	
	# global I
	I = gsm.get_interface(args.interface)()
	
	app.run(host='localhost', port=port)