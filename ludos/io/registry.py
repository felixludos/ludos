import os
import yaml

from omnibelt import Registry

from ..util import get_printer, load_yaml
from ..errors import RegistryCollisionError, InvalidValueError

prt = get_printer(__name__)

_game_registry = Registry()
def register_game(cls, name=None, path=None, info=None):
	if name is None:
		name = cls.__name__
	
	if info is None and path is not None:
		info = load_yaml(path, 'r')
	elif info is None:
		info = {'short_name':name}
	elif 'short_name' not in info:
		prt.warning('No short_name for game {} found, defaulting to {}'.format(name, name))
		info['short_name'] = name
	
	info['cls'] = cls
	
	registry = _game_registry
	
	name = info['short_name']
	if name in registry:
		prt.warning('{} is already registered, updating info'.format(name))
		registry[name].update(info)
	else:
		prt.debug('Registering game: {}'.format(name))
		registry[info['short_name']] = info
	
	cls.info = registry[name]

# info['start_phase'] = cls._start_phase
	# assert info['start_phase'] is not None, f'No start phase for {name}'

def Game(name=None, info_path=None):
	
	def _reg_game(cls):
		nonlocal name, info_path
		
		if name is None:
			name = cls.__name__
		cls.name = name
		
		game_path = cls.__home__
		
		if info_path is None:
			info_path = os.path.join(game_path, 'info.yaml')
		elif not os.path.isfile(info_path):
			info_path = os.path.join(game_path, info_path)
		
		if os.path.isfile(info_path):
			info = yaml.load(open(info_path, 'r'))
			cls.info = info
		else:
			info = {}
			prt.error('Game info for {} not found.'.format(cls.name))
		
		# register game
		register_game(cls, info=info)
		
		return cls
	
	return _reg_game

def register_object(game, name=None, cls=None, open=None, req=None):
	assert cls is not None or name is not None, 'no name or class provided'
	
	if cls is not None:
		name = cls.obj_type
	
	if game not in _game_registry:
		prt.warning('Registering the GameObject {} for a game before registering the game {}'.format(name, game))
		_game_registry[game] = {}
	
	info = _game_registry[game]
	
	if 'objects' not in info:
		info['objects'] = {}
	
	objs = info['objects']
	
	if name in objs:
		prt.info('{} already registered, so updating entry'.format(name))
	else:
		objs[name] = {}
	
	obj = objs[name]
	
	obj['name'] = name
	obj['open'] = open
	obj['req'] = req
	
	if cls is not None:
		obj['cls'] = cls

def register_object_dec(game, name=None, open=None, req=None):
	
	def _reg_obj(cls=None):
		nonlocal game, name, open, req
		register_object(game, name=name, cls=cls, open=open, req=req)
		return cls
			
	return _reg_obj
	
	
def register_phase(game, cls, name=None, start=False):
	if game not in _game_registry:
		prt.warning('Registering the GamePhase {} for a game before registering the game {}'.format(name, game))
		_game_registry[game] = {}
	
	info = _game_registry[game]
	
	if start:
		if 'start_phase' in info:
			prt.warning('The start phase {} for {} has already been registered, and is now replaced by {}'.format(
				info['start_phase'], game, name,
			))
		info['start_phase'] = name
	
	if 'phases' not in info:
		info['phases'] = {}
	
	phases = info['phases']
	
	if name in phases:
		prt.info('{} already registered, so updating entry'.format(name))
	else:
		phases[name] = {}
	
	phase = phases[name]
	
	phase['cls'] = cls
	phase['start'] = start
	
def register_phase_dec(game, start=False):
	
	def _reg_phase(cls):
		nonlocal game, start
		name = cls.name
		register_phase(game=game, cls=cls, name=name, start=start)
		return cls
		
	return _reg_phase


def register_player_type(game, cls, name=None, open=None, default=False):
	if game not in _game_registry:
		prt.warning('Registering player type {} for a game before registering the game {}'.format(name, game))
		_game_registry[game] = {}
	
	info = _game_registry[game]

	if name is None:
		prt.warning(f'No name provided for player type: {cls}')
		name = cls.obj_type
		
	if 'player_types' not in info:
		info['player_types'] = {}
		
	players = info['player_types']
	
	if name not in players:
		players[name] = {}
	else:
		prt.warning(f'A player type {name} has already been registered, overwriting now.')
		
	player = players[name]
	
	player['cls'] = cls
	player['name'] = name
	if open is not None:
		player['open'] = open
	player['default'] = default

def register_player_type_dec(game, name=None, open=None):
	def _reg_ply(cls=None):
		nonlocal game, name, open
		register_object(game, name=name, cls=cls, open=open)
		return cls
	
	return _reg_ply
	

_interface_registry = {}
def register_interface(name, cls):
	if name in _interface_registry:
		raise RegistryCollisionError(name)
	_interface_registry[name] = cls
def get_interface(name):
	if name not in _interface_registry:
		raise InvalidValueError(name)
	return _interface_registry[name]


_ai_registry = {}
_game_ai_registry = {}
def register_ai(name, cls, game=None):
	if game is not None:
		if game not in _game_ai_registry:
			_game_ai_registry[game] = {}
		_game_ai_registry[game][name] = cls
		return
	if name in _ai_registry:
		raise RegistryCollisionError(name)
	_ai_registry[name] = cls
def available_ai(name, game=None):
	if game is not None and name in _game_ai_registry[game]:
		return _game_ai_registry[game][name]
	return _ai_registry[name]
def get_ai(name=None, game=None):
	assert name is not None or game is not None, 'nothing selected'
	if game is not None and game in _game_ai_registry:
		if name is None:
			if game not in _game_ai_registry:
				raise InvalidValueError(game)
			ais = _ai_registry.copy()
			ais.update(_game_ai_registry[game])
			return ais
		elif name in _game_ai_registry[game]:
			return _game_ai_registry[game][name]
	
	if name not in _ai_registry:
		raise InvalidValueError(name)
	return _ai_registry[name]

_trans_registry = {}
def register_trans(name, cls):
	if name in _trans_registry:
		raise RegistryCollisionError(name)
	_trans_registry[name] = cls
def get_trans(name):
	if name not in _trans_registry:
		raise InvalidValueError(name)
	return _trans_registry[name]
