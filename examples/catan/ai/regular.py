import sys, os
import numpy as np

from scipy.special import softmax

from ..main import MY_PATH

import gsm
from gsm import tdict, tlist, tset
from gsm import ai
from gsm.viz import _package_action

from .ops import compute_missing, count_vp

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
		self.register_tactic(Regular.robber_loc('robber', 'loc', self.gen if self.stochastic else None))
		
		# setup: loc-road, loc-settlement
		self.register_tactic(Regular.setup_settlement('setup', 'loc-settlement', self.gen if self.stochastic else None))
		
		# register config files
		self.register_config('rules', os.path.join(MY_PATH, 'config/rules.yaml'))
		self.register_config('dev', os.path.join(MY_PATH, 'config/dev_cards.yaml'))
		self.register_config('map', os.path.join(MY_PATH, 'config/map.yaml'))
		
		config = self.load_config()
		# self.mind.costs = config.rules.building_costs
		self.mind.rules = config.rules
		self.mind.res_idx = {r:i for i,r in enumerate(config.rules.res_names)}
	
	def think(self, me, table, opponents, **status):
		
		# me.resources
		# me.vps
		# me.buildings.road
		
		for player in opponents:
			player.vps = count_vp(player.buildings, self.mind.rules.victory_points)
		

	class setup(ai.mindset.Random_Mindset):
		pass
	class setup_settlement(ai.mindset.Random_Tactic):
		def get_sites(self, options, table):
			sites = np.array([tdict(ID=a[0].ID) for a in options['loc-settlement']])
			for site in sites:
				c = table[site['ID']]
				site.nums = tlist(n.num for n in c.fields if n is not None and 'num' in n)
				site.ress = tlist(n.res for n in c.fields if n is not None and 'res' in n)
				site.val = sum(6 - abs(n - 7) for n in site.nums)
				if 'port' in c:
					site.port = c.port
			return sites
		
		def get_nums(self, site):
			nums = np.zeros(11, dtype=int)
			for n in site.nums:
				nums[n - 2] += 1
			return nums
		
		def get_res(self, ress, res_idx):
			res = np.zeros(5)
			for r in ress:
				if r in res_idx:
					res[res_idx[r]] += 1
			return res
		
		def observe(self, mind, me, options, table, **status):
			
			if 'first' not in self:
			
				sites = self.get_sites(options, table)
				vals = np.array([site.val for site in sites])
				top = np.argsort(-vals)[:5]
				wts = softmax(vals[top])
			
				idx = top[0] if self.gen is None else self.gen.choices(top, weights=wts)[0]
				
				first = sites[idx]
				self.first = first
				return
			
			sites = self.get_sites(options, table)
			
			nums = self.get_nums(self.first)
			alln = np.stack([self.get_nums(site) for site in sites])
			priority = 6 - np.abs(np.arange(11) - 5)
			values = priority / (nums / 3 + 1)
			
			dnum = (alln * values).sum(-1)
			n_wts = softmax(dnum)
			
			count = self.get_res(self.first.ress, mind.res_idx)
			allr = np.stack([self.get_res(site.ress, mind.res_idx) for site in sites])
			rval = (count + allr).clip(0, 1).sum(-1)
			r_wts = softmax(rval)
			
			wts = n_wts * r_wts
			wts = wts / wts.sum()
		
			idx = wts.argmax() if self.gen is None else self.gen.choices(np.arange(len(wts)), weights=wts)[0]
			
			self.second = sites[idx]
		
		def decide(self, mind, actions):
			pick = self.second if 'second' in self else self.first
			return [pick.ID]

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
		def observe(self, mind, me, options, table, opponents, **status):
			hexs = tlist(table[a.ID] for a, in options['loc'])
			
			remaining = tlist()
			for h in hexs:
				if 'num' in h:
					for c in h.corners:
						if 'building' in c and c.building.player.name != me.name and c.building.player.num_res > 0:
							info = tdict()
							info.val = 6 - abs(h.num - 7)
							info.res = h.res
							info.ID = h._id
							info.vp = c.building.player.vps
							remaining.append(info)
			
			self.remaining = remaining
			
		def decide(self, mind, actions):
			cruelty = 3  # as this increases, vps make less of a difference, and its just about the numbers
			wts = softmax([p.vp/cruelty + p.val for p in self.remaining])
			
			pick = self.remaining[wts.argmax()].ID if self.gen is None else self.gen.choices(self.remaining, weights=wts)[0].ID
			
			return [pick]
			
ai.register_ai('regular', Regular, game='catan')



