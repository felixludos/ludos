

import numpy as np
from ludos import GameOver, GamePhase, GameActions, GameObject
from ludos import gset, gdict, glist
from ludos import PhaseComplete, SwitchPhase, SubPhase
from ludos.common import stages as stg

class BuildPhase(stg.StagePhase, name='build', game='aristocracy'):

	@stg.Entry_Stage('choose')
	def build_types(self, C, player, action=None):

		pass
	