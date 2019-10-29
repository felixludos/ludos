import json
from humpack import Savable, Transactionable
from .. import tdict, tset, tlist
from ..mixins import Named
from .. import Interface, containerify, RandomGenerator
from ..viz import _package_action
from ..core.actions import decode_action_set
from ..io import get_ai, register_interface, register_ai

class Agent_Interface(Interface):
	def __init__(self, *users, agent_type=None, host_addr=None):
		super().__init__(*users, host_addr=host_addr)
		self.agents = {user:None for user in users}
		self.agent_type = agent_type
	
	def set_player(self, user, player):
		super().set_player(user, player)
		self.agents[user] = get_ai(self.agent_type)(player)
	
	def ping(self):
		return 'ping reply from: {}'.format(', '.join(self.users))
	
	def step(self, user, msg):
		msg = containerify(msg)
		
		if 'error' in msg:
			print('*** ERROR: {} ***'.format(msg.error.type))
			print(msg.error.msg)
			print('****************************')
			out = {'error': 'received error', 'received': msg.error}
			return json.loads(out)
		
		out = {}
		
		if 'key' in msg:
			out['key'] = msg.key
			
		agent = self.agents[user]
		player = agent.name
		me = msg.players[player]
		# del msg.players[player] # remove self from players list
		
		agent.observe(me, **msg)
		
		if 'options' in msg:
			
			options = tdict()
			for name, opts in msg.options.items():
				options[name] = decode_action_set(opts)
			
			out['action'] = agent.decide(options)
		
		return json.dumps(out)
	
	def reset(self, user):
		if self.agents[user] is not None:
			self.agents[user].reset()
	
register_interface('agent', Agent_Interface)

class Agent(Named, tdict):
	# def __init__(self, name): # player name
	# 	super().__init__(name)
	# 	self.msg = None
	
	def reset(self):
		pass
	
	# Optional override - to use data from current status
	def observe(self, me, **status):
		pass
	
	# Required override - choose from possible actions
	def decide(self, options):
		raise NotImplementedError
	
	
class RandomAgent(Agent):
	def __init__(self, name, seed=None):
		super().__init__(name)
		self.gen = RandomGenerator()
		if seed is not None:
			self.gen.seed(seed)
	
	def decide(self, options):
		actions = []
		for name, opts in options.items():
			actions.extend((name, _package_action(o)) for o in opts)
			
		return self.gen.choice(actions)

register_ai('random', RandomAgent)
