import yaml
from ..signals import RegistryCollisionError, InvalidValueError


_game_registry = {}
def register_game(cls, path):
	info = yaml.load(open(path, 'r'))
	_game_registry[info['short_name']] = cls, info


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
	if game is not None:
		if name is not None:
			return _game_ai_registry[game][name]
		if game not in _game_ai_registry:
			raise InvalidValueError(game)
		ais = _ai_registry.copy()
		ais.update(_game_ai_registry[game])
		return ais
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
