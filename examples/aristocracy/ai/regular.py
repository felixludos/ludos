import sys, os
import numpy as np

from scipy.special import softmax

from ..main import MY_PATH

import gsm
from gsm import tdict, tlist, tset
from gsm import ai
from gsm.viz import _package_action

# from .ops import compute_missing, count_vp

# Phases

# main: pre, cancel, dev-res, pass, build-road, build-settlement, build-city, buy, maritime-trade, domestic-trade, play
# robber: loc, target
# setup: loc-road, loc-settlement
# trade: cancel, maritime-trade, domestic-confirm, domestic-response, send, domestic-trade



class Regular(ai.ConfigAgent, ai.Mindset_Agent):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		# robber: loc, target
		# self.register_tactic(Regular.robber_loc('robber', 'loc', self.gen if self.stochastic else None))
		
		# setup: loc-road, loc-settlement
		# self.register_tactic(Regular.setup_settlement('setup', 'loc-settlement', self.gen if self.stochastic else None))
		
		# register config files
		# self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		# self.register_config('dev', os.path.join(MY_PATH, 'config/dev_cards.yaml'))
		# self.register_config('map', os.path.join(MY_PATH, 'config/map.yaml'))
		
		# config = self.load_config()
		# self.mind.costs = config.rules.building_costs
		# self.mind.rules = config.rules
		# self.mind.res_idx = {r:i for i,r in enumerate(config.rules.res_names)}
	
	def think(self, me, table, opponents, **status):
		pass

			
ai.register_ai('regular', Regular, game='aristocracy')



