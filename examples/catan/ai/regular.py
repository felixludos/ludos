import sys, os
import numpy as np

from ..main import MY_PATH

import gsm
from gsm import tdict, tlist, tset
from gsm import ai

from .ops import compute_missing

# Phases

# main: pre, cancel, dev-res, pass, build-road, build-settlement, build-city, buy, maritime-trade, domestic-trade, play
# robber: loc, target
# setup: loc-road, loc-settlement
# trade: cancel, maritime-trade, domestic-confirm, domestic-response, send, domestic-trade



class Regular(ai.ConfigAgent, ai.Mindset_Agent):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		# main: pre, cancel, dev-res, pass, build-road, build-settlement, build-city, buy, maritime-trade, domestic-trade, play
		
		# self.register_tactic(Regular.main_build_road('main', 'build-road', self.gen))
		# self.register_tactic(Regular.main_build_road('main', 'build-settlement', self.gen))
		# self.register_tactic(Regular.main_build_road('main', 'build-city', self.gen))
		
		# robber: loc, target
		self.register_tactic(Regular.robber_loc('robber', 'loc', self.gen))
		
		# setup: loc-road, loc-settlement
		
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		self.register_config('dev', os.path.join(MY_PATH, 'config/dev_cards.yaml'))
		self.register_config('map', os.path.join(MY_PATH, 'config/map.yaml'))
		
		config = self.load_config()
		self.mind.costs = config.rules.building_costs
	
	def think(self, me, players, table, **status):
		
		# me.resources
		# me.vps
		# me.buildings.road
		
		pass

	class setup(ai.mindset.Random_Mindset):
		pass
	class setup_settlement(ai.mindset.Random_Tactic):
		pass

	class main(ai.mindset.Random_Mindset):
		def observe(self, mind, me, **status):
			pass
		def prioritize(self, mind, groups):
			raise NotImplementedError  # returns array of floats of corresponding priorities of each group
	
	class main_build_road(ai.mindset.Random_Tactic):
		def observe(self, mind, me, **status):
			pass
		def priority(self, mind, actions):
			return 0.
		def decide(self, mind, actions):
			raise NotImplementedError
	class main_build_settlement(ai.mindset.Random_Tactic):
		pass
	class main_build_city(ai.mindset.Random_Tactic):
		pass
	
	class robber(ai.mindset.Random_Mindset):
		def observe(self, mind, me, **status):
			
			pass
		def prioritize(self, mind, groups):
			raise NotImplementedError  # returns array of floats of corresponding priorities of each group
		
	class robber_loc(ai.mindset.Random_Tactic):
		def observe(self, mind, me, options, table, **status):
			hexs = tlist(table[a.ID] for a, in options['loc'])
			
			remaining = tlist()
			for h in hexs:
				for c in h.corners:
					if 'building' in c and c.building.player.name != 'White' and c.building.player.num_res > 0:
						remaining.append(h)
						break
			
			picks = tlist()
			for h in remaining:
				info = tdict()
				info.val = 5 - abs(h.num - 7)
				info.res = h.res
				info.ID = h._id
				picks.append(info)
			
			
			
			print(picks.keys())
			
			
		def decide(self, mind, actions):
			raise NotImplementedError
			
ai.register_ai('regular', Regular, game='catan')



