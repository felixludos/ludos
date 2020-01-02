
from .. import tdict, tlist, tset
from .. import GamePhase, PhaseComplete, GameActions

class Responsive(object): # mixin
	def respond(self, code, *args, **kwargs):
		return self.__getattribute__(code)(*args, **kwargs)

class ResponsePhase(GamePhase):
	def __init__(self, player, caller, options,
	             status=None, desc=None, **kwargs):
		super().__init__(name=None, player=player,
		                 status=status, desc=desc,
		                 caller=caller, options=options, kwargs=kwargs)
	
	def execute(self, C, player=None, action=None):
		
		if action is None:
			return
		
		choice = action[0]
		response = self.options[choice] \
			if isinstance(self.options, dict) else choice
		
		self.caller.respond(response, **self.kwargs)
		
		raise PhaseComplete
	
	def encode(self, C):
		
		out = GameActions(self.status)
		
		choices = self.options.keys() \
			if isinstance(self.options, dict) else self.options
		choices = tset(choices)
		
		with out('question', self.desc):
			out.add(choices)
		
		return tdict({self.player:out})


