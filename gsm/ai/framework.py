import json
from humpack import Savable, Transactionable
from .. import tdict, tset, tlist
from ..mixins import Named
from .. import Interface, RandomGenerator, unjsonify
from ..viz import _package_action
from ..core.actions import decode_action_set
from ..io import get_ai, register_interface, register_ai

class Agent_Interface(Interface):
	def __init__(self, *users, agent_type=None, host_addr=None, **agent_kwargs):
		super().__init__(*users, host_addr=host_addr)
		self.agents = {user:None for user in users}
		assert agent_type is not None
		self.agent_type = agent_type
		self.agent_kwargs = agent_kwargs
	
	def set_player(self, user, player):
		super().set_player(user, player)
		self.agents[user] = get_ai(self.agent_type)(player, **self.agent_kwargs)
		print('Agent for {} is initialized'.format(user))
	
	def ping(self):
		return 'ping reply from {} agent/s: {}'.format(self.agent_type, ', '.join(self.users))
	
	def step(self, user, msg):
		msg = unjsonify(msg)
		
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
				options[name] = decode_action_set(opts.actions)
			
			out['group'], out['action'] = agent.decide(options)
		
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
		self.seed = seed
		self.reset()
	
	def reset(self):
		if self.seed is not None:
			self.gen.seed(self.seed)
			print('Reset seed to: {}'.format(self.seed))
	
	def decide(self, options):
		actions = []
		for name, opts in options.items():
			actions.extend((name, _package_action(o)) for o in opts)
			
		return self.gen.choice(actions)

register_ai('random', RandomAgent)
