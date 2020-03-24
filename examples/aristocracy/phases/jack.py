
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import PhaseComplete, SwitchPhase
from gsm.common import stages as stg
from gsm import util

from .royals import RoyalPhase


class JackPhase(RoyalPhase, game='aristocracy', name='jack'):
	@stg.Stage('pre')
	def pre(self, C, player, action=None):
		
		for p in C.players:
			if p.money > 0:
				raise stg.Switch('auction')
			
		C.log.writef('No one has any money, so the auction is skipped')
		raise stg.Switch('market')
		
	@stg.Stage('auction')
	def run_auction(self, C, player, action=None):
		if action is None:
			self.bids = tdict({p:0 for p in C.players if p.money == 0})
		else:
			bid, = action
			self.bids[player] = bid
			
			if len(self.bids) == len(C.players):
				
				# resolve auction
				mx, cost = None, None
				for p, bid in self.bids.items():
					C.log.writef('{} bids {}', p, bid)
					if mx is None or bid > mx:
						cost = mx
						mx = bid
				
				if cost is None:
					cost = 0
				if mx > 0:
					self.cost = cost
					winners = tlist(p for p, bid in self.bids.items() if bid == mx)
					self.winners = util.sort_by(winners, [p.order for p in winners])
					raise stg.Switch('collection')
				else:
					C.log.writef('No one bid anything')
				
				raise stg.Switch('market')
		
		raise stg.Decide('auction')
	
	@stg.Decision('auction', ['bid'])
	def choose_bid(self, C):
		
		outs = tdict()
		
		for p in C.players:
			if p not in self.bids:
				out = GameActions('How much do you want to bid in the auction?')
				with out('bid', 'Your bid'):
					out.add(tset(range(p.money+1)))
				outs[p] = out
		
		return outs
	
	@stg.Stage('collection')
	def collection(self, C, player, action=None):
		
		if action is None:
			self.picks = tdict()
		else:
			pick, = action
			self.picks[player] = pick
			
			C.log.writef('{} chooses {}', player, pick)
			
			if len(self.picks) == len(self.winners):
				
				# resolve picks
				sel = tdict()
				for p, pick in self.picks.items():
					if pick not in sel:
						sel[pick] = tset()
					sel[pick].add(p)
				
				for card, ps in sel.items():
					if len(ps) == 1:
						p = ps.pop()
						card.visible.clear()
						card.visible.add(p)
						p.money -= self.cost
						C.log.writef('{} gains {} for {}', p, util.format_quantity(str(card)),
						             util.format_quantity('coin',self.cost))
					else:
						C.log.writef('{} is removed because it was selected by: {}'
						             .format(str(card), ', '.join(['{}']*len(ps))), *ps)
						C.state.market.remove(card)
		
		raise stg.Decide('collection')
	
	@stg.Decision('collection', ['pick'])
	def collect(self, C):
		
		player = self.winners[len(self.picks)]
		
		out = GameActions('What card do you choose in the auction?')
		
		with out('pick', 'Claim card'):
			out.add(C.state.market.neutral)
		
		return tdict({player:out})
	
	@stg.Stage('post')
	def post(self, C, player, action=None):
		for p in C.players:
			for farm in p.buildings.farm:
				if farm.harvest is None:
					card = C.state.deck.draw()
					card.visible.clear()
					farm.harvest = card
					C.log.writef('{} is harvestable on {}\'s {}', card, p, farm)

		raise SwitchPhase('king')