
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import PhaseComplete, SwitchPhase, SubPhase
from gsm.common import stages as stg

from ..ops import satisfies_vic_req, get_next_market

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


		





		
