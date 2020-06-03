

import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import PhaseComplete, SwitchPhase, SubPhase
from gsm.common import stages as stg

class BuildPhase(stg.StagePhase, name='build', game='aristocracy'):

	@stg.Entry_Stage('choose')
	def build_types(self, C, player, action=None):

		pass
	