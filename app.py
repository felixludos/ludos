import json
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

class ActionConverter(BaseConverter):

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

#region FRONT routes
app = Flask(__name__, static_folder='static')
app.url_map.converters['action'] = ActionConverter
CORS(app)

statfold_sim = 'templates'
statfold_path = 'static'

@app.route('/sim')
@app.route('/sim/')
def rootsim():
	return send_from_directory(statfold_sim, 'game.html')

@app.route('/<path:path>')
def rootsimPath(path):
	res = send_from_directory('', path)
	return send_from_directory('', path)

#endregion

@app.route('/get_UI_spec/<game>')
def _get_UI_spec(game):
	path = userSpecYmlPath(game)
	res = ymlFile_jString(userSpecYmlPath(game))
	return res

@app.route('/init/<game>')
def _init(game):
	res = I.init(game)
	return res

@app.route('/restart/<player>')
def _restart(player):
	res = I.restart()
	return res

@app.route('/action/<player>/<index>')
def _action(player, index):
	ituple = int(index)
	res = I.move(None, ituple)
	return res

I = Game()
#I.init()

if __name__ == "__main__":
	app.run(host='localhost', port=5000)