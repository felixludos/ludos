
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist

class Selection(tdict):
	def __init__(self, players, allow_multiple=True,
	             log=None, status=None,
	             options=None, source=None, key=None, option_fn=None):
		super().__init__(players=players, allow_multiple=allow_multiple,
		                 log=log, done=False)
		self.sel = tdict()
		self.done = tdict()
		
		if options is not None:
			option_fn = lambda p: options
		elif key is not None and source is not None:
			option_fn = lambda p: source[p][key]
		assert option_fn is not None, 'no option list provided'
		
		self.option_fn = option_fn
		
		if status is None:
			status = 'You may make a selection'
		self.status = status
		
	def is_done(self):
		return self.done if len(self.done) == len(self.players) else None
	
	def step(self, player, action):
		
		cmd, = action
		
		if self.allow_multiple:
		
			if cmd == 'complete':
				self.done[player] = self.sel[player]
			
			elif cmd in self.sel[player]:
				if self.log is not None:
					self.log[player].writef('You have deselected {}', cmd)
				self.sel[player].remove(cmd)
			
			else:
				if self.log is not None:
					self.log[player].writef('You have selected {}', cmd)
				self.sel[player].add(cmd)
		
		else:
			self.done[player] = cmd
		
		return self.is_done()
	
	def options(self):
		
		outs = tdict()
		
		for p in self.players:
			if p not in self.done:
				out = GameActions(self.status)
				
				with out('complete', 'You are done with the selection.'):
					if self.allow_multiple:
						out.add('complete')
				
				options = self.option_fn(p) - self.sel[p]
				with out('select', 'Select an option'):
					if len(options):
						out.add(options)
				
				with out('deselect', 'Deselect an option'):
					if len(self.sel[p]):
						out.add(self.sel[p])
				
				outs[p] = out
		
		return outs
		


