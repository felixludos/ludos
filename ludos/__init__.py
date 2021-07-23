# from humpack import containerify
#
# from humpack import adict as gdict, tlist as glist, tset as gset, \
# 	tdeque as gdeque, tstack as gstack, theap as gheap
#
# from humpack.wrappers import Array
# from humpack import Packable, Transactionable
# from .util import jsonify, unjsonify, obj_unjsonify
# from .signals import PhaseComplete, SwitchPhase, GameOver, SubPhase
# from .writing import write, writef, RichText
# from .util import RandomGenerator, assert_
# from .io import Host, Interface, Test_Interface, register_game, register_interface, get_interface, send_http
# from .io import register_game, register_ai, register_interface, register_object
# from . import viz
# from . import common
# from . import ai
# from . import io
# from .core import GamePhase, GameStack, GamePlayer, GameActions, GameObject, GameTable, GameState, GameLogger, GameObjectGenerator, GameController, GameManager, SafeGenerator
#
# import os
# __info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
# with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
# 	exec(f.read(), __info__)
# del os
# del __info__['__file__']
# __author__ = __info__['author']
# __version__ = __info__['version']

from . import test

import omnifig as fig

import random
import os
import anvil.server

import gsm
import gsm.dummy

@fig.Script('uplink')
def _uplink(A):
	
	print('preparing')
	
	key = os.environ['ANVIL_UPLINK_KEY']
	anvil.server.connect(key)
	
	T = gsm.GameTable()
	
	@anvil.server.callable
	def hard_reset():
		print('Resetting table')
		global T
		T = gsm.GameTable()
	
	@anvil.server.callable
	def get_games():
		return T.get_available_games()
	
	@anvil.server.callable
	def set_game(game):
		T.set_game(game)
		print(f'set game: {game}')
	
	@anvil.server.callable
	def add_players(players):
		for player in players:
			T.add_player(player)
		print(f'added players: {players}')
	
	@anvil.server.callable
	def start_game():
		T.start_game()
		# random.seed(10)
		print('started game')
	
	@anvil.server.callable
	def get_status(user):
		print(f'Getting status of {user}')
		return T.get_status(user)
	
	print('Connected and waiting.')
	
	anvil.server.wait_forever()






