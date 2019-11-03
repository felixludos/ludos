
from ..mixins import Named, Typed
from .registry import register_interface


class Interface(Typed, object):
	def __init__(self, *users, host_addr=None):
		super().__init__(self.__class__.__name__)
		self.users = {user:None for user in users}
		self.host = host_addr
	
	def set_player(self, user, player):
		self.users[user] = player
	
	def ping(self):
		return 'ping reply'
	
	def reset(self, user):
		return 'Interface Reset'
	
	def step(self, user, msg):
		raise NotImplementedError
	
	def save(self):
		return '{}'
	
	def load(self, state):
		pass

class Test_Interface(Interface):
	def ping(self):
		print('ping')
		return 'ping reply from test interface'
	
	def set_player(self, user, player):
		print('{} : {}'.format(user, player))
		return 'set_player'
	
	def reset(self, user):
		print('reset')
		return 'Interface Reset'
	
	def step(self, user, msg):
		print('step')
		print(msg)
		return 'nothing'
	
	def save(self):
		return 'save'
	
	def load(self, state):
		return 'load'

register_interface('test', Test_Interface)


