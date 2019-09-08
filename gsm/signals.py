


class GameOver(Exception):
	pass

class PhaseComplete(Exception):
	pass

class PhaseInterrupt(Exception): # possibly can include an action and player
	def __init__(self, phase):
		super().__init__()
		self.phase = phase
		
	def get_phase(self):
		return self.phase

