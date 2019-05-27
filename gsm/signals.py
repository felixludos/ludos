



class PhaseComplete(Exception):
	pass

class PhaseInterrupt(Exception): # possibly can include an action and player
	def __init__(self, phase, player=None, action=None):
		super().__init__()
		self.phase = phase
		self.player = player
		self.action = action

