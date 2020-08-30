
import numpy as np
from ludos import GameOver, GamePhase, GameActions, GameObject
from ludos import gset, gdict, glist
from ludos import PhaseComplete, SwitchPhase, SubPhase
from ludos.common import stages as stg

class RoyalPhase(stg.StagePhase):
	
	@stg.Entry_Stage('init')
	def init(self, C, player, action=None):
		
		C.neutral.reset(self.neutral_num)
		
		for p in C.players:
			p.draw_cards(log=C.log)
		
		raise stg.Switch('pre')
	
	@stg.Stage('pre')
	def pre_phase(self, C, player, action=None):
		raise NotImplementedError
	
	@stg.Stage('market')
	def run_market(self, C, player, action=None):
		self.set_current_stage('post')
		raise SubPhase('market', origin=self.name)
	
	@stg.Stage('post')
	def post_phase(self, C, player, action=None):
		raise NotImplementedError


		





		
