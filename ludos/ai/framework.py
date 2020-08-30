import json, yaml
from humpack import Packable, Transactionable, json_pack, json_unpack
from .. import gdict, gset, glist, containerify
from ..mixins import Named
from .. import Interface, RandomGenerator, unjsonify, obj_unjsonify, util
from ..viz import _package_action
from ..core.actions import decode_action_set
from ..io import get_ai, register_interface, register_ai

class Agent_Interface(Interface):
	def __init__(self, *users, agent_type=None, game=None, host_addr=None, **agent_kwargs):
		super().__init__(*users, host_addr=host_addr)
		self.agents = {user:None for user in users}
		assert agent_type is not None
		self.agent_type = agent_type
		self.agent_kwargs = agent_kwargs
		self.game = game
	
	def set_player(self, user, player):
		super().set_player(user, player)
		ai_cls = get_ai(self.agent_type, game=self.game)
		self.agents[user] = ai_cls(player, **self.agent_kwargs)
		print('Agent for {} is initialized'.format(user))
	
	def ping(self):
		return 'ping reply from {} agent/s: {}'.format(self.agent_type, ', '.join(self.users))
	
	def step(self, user, msg):
		msg = unjsonify(msg)
		util.obj_cross_ref(msg, {'_obj':msg.table, '_player':msg.players})
		for ID, obj in msg.table.items():
			obj._id = ID
		
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
		msg.opponents = msg.players.copy()
		del msg.opponents[player] # remove self from players list
		msg.opponents = glist(msg.opponents.values())
		options = gdict()
		if 'options' in msg:
			for name, opts in msg.options.items():
				options[name] = decode_action_set(opts.actions)
		msg.options = options
		# msg.groups = tlist(msg.options.keys())
		
		agent.observe(me, **msg)
		
		if 'options' in msg:
			out['group'], out['action'] = agent.decide(options)
		
		return json.dumps(out)
	
	def reset(self, user):
		if self.agents[user] is not None:
			self.agents[user].reset()
			
	def save(self):
		return {user:json_pack(agent) for user, agent in self.agents.items()}
	
	def load(self, state):
		self.agents = {user:json_unpack(data) for user, data in state.items()}
		
	def __str__(self):
		return '{}({})'.format(super().__str__(), self.agent_type)
	
register_interface('agent', Agent_Interface)

class Agent(Named, gdict):
	# def __init__(self, name): # player name
	# 	super().__init__(name)
	# 	self.msg = None
	
	def _fmt_error(self, cmd):
		print('\n\nException occurred for {}'.format(self.name))
	
	def reset(self):
		try:
			return self._reset()
		except Exception as e:
			self._fmt_error('reset')
			raise e
	
	def _reset(self):
		pass
	
	# Optional override - to use data from current status
	def observe(self, me, **status):
		try:
			return self._observe(me, **status)
		except Exception as e:
			self._fmt_error('observe')
			raise e
	
	def _observe(self, me, **status):
		pass
	
	# Required override - choose from possible actions
	def decide(self, options):
		try:
			return self._decide(options)
		except Exception as e:
			self._fmt_error('decide')
			raise e
	
	def _decide(self, options):
		raise NotImplementedError
	
class ConfigAgent(Agent): # mixin only, this isnt a full agent
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.config_registry = gdict()
		
	def register_config(self, name, path):
		self.config_registry[name] = path
		
	def load_config(self):
		config = gdict()
		
		for name, path in self.config_registry.items():
			config[name] = containerify(yaml.load(open(path, 'r')))
			
		return config

class RandomAgent(Agent):
	def __init__(self, name, seed=None):
		super().__init__(name)
		self.gen = RandomGenerator()
		self.seed = seed
		self.reset()
	
	def _reset(self):
		if self.seed is not None:
			self.gen.seed(self.seed)
			print('Reset seed to: {}'.format(self.seed))
	
	def _decide(self, options):
		actions = []
		for name, opts in options.items():
			actions.extend((name, self.package_action(o)) for o in opts)
			
		return self.gen.choice(actions)
	
	def package_action(self, action):
		return _package_action(action)

register_ai('random', RandomAgent)


class PassingAgent(RandomAgent):
	def __init__(self, name, prob=0.5, seed=None, groups=['pass', 'cancel']):
		super().__init__(name, seed=seed)
		self.prob = prob
		self.groups = groups
		
	def _decide(self, options):
		if self.gen.uniform(0,1) < self.prob:
			for group in self.groups:
				if group in options:
					return group, self.package_action(options[group].pop())
		
		return super()._decide(options)
		
register_ai('pass', PassingAgent)


class AgentComposer(Agent):
	def __init__(self, name, agents=[]): # each agent element has: [agent_type, game, kwargs]
		super().__init__(name)
		self.agents = [get_ai(agent_type, game)(name, **kwargs)
		               for agent_type, game, kwargs in agents]
		assert len(agents), 'no agents provided'
		self.active = None
		
	def process(self, agent, me, **status):
		return 0
		
	def _observe(self, me, **status):
		max_rank, best_agent = None, None
		
		for agent in self.agents:
			rank = self.process(agent, me, **status)
			if max_rank is None or rank > max_rank:
				max_rank, best_agent = rank, agent
		
		self.active = best_agent
		self.active._observe(me, **status)
		
	def _decide(self, options):
		return self.active._decide(options)

register_ai('composer', AgentComposer)
