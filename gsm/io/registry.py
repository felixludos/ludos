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
def register_ai(name, cls):
	if name in _ai_registry:
		raise RegistryCollisionError(name)
	_ai_registry[name] = cls
def get_ai(name):
	if name not in _ai_registry:
		raise InvalidValueError(name)
	return _ai_registry[name]

