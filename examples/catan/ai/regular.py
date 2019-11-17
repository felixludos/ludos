import sys, os
import numpy as np

from ..main import MY_PATH

import gsm
from gsm import ai

from .ops import compute_missing

# Phases

# main: pre, cancel, dev-res, pass, build-road, build-settlement, build-city, buy, maritime-trade, domestic-trade, play
# robber: loc, target
# setup: loc-road, loc-settlement
# trade: cancel, maritime-trade, domestic-confirm, domestic-response, send, domestic-trade



class Regular(ai.Mindset_Agent, ai.ConfigAgent):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
	
		self.register_tactic(Regular.main_build_road('main', 'build-road', self.gen))
		self.register_tactic(Regular.main_build_road('main', 'build-settlement', self.gen))
		self.register_tactic(Regular.main_build_road('main', 'build-city', self.gen))
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		self.register_config('dev', os.path.join(MY_PATH, 'config/dev_cards.yaml'))
		self.register_config('map', os.path.join(MY_PATH, 'config/map.yaml'))
		self.register_config('msgs', os.path.join(MY_PATH, 'config/msgs.yaml'))
		
		config = self.load_config()
		self.mind.costs = config.building_costs
	
	def think(self, me, players, table, **status):
		
		# me.resources
		# me.vps
		# me.buildings.road
		
		pass

	class main_ms(ai.mindset.Random_Mindset):
		def observe(self, mind, me, **status):
			
			pass
		def prioritize(self, mind, group):
			pass

	class main_build_road(ai.mindset.Random_Tactic):
		def decide(self, mind, actions):
			pass
	class main_build_settlement(ai.mindset.Random_Tactic):
		pass
	class main_build_city(ai.mindset.Random_Tactic):
		pass

ai.register_ai('regular', Regular, game='catan')



