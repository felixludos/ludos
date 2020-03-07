import numpy as np
from gsm import GamePhase, GameActions, PhaseComplete
from gsm import tset, tdict, tlist
from gsm import writef, assert_

from gsm.common import stages as stg

from ..ops import trade_available, execute_trade


class TradePhase(stg.StagePhase, name='trade', game='catan'):
	
	def __init__(self, player, bank_trades=None, **info):
		super().__init__(**info)
		
		self.player = player
		self.demand = tdict({res: 0 for res in player.resources.keys()})
		self.offer = tdict({res: 0 for res in player.resources.keys()})
		
		self.maritime = bank_trades
		self.maritime_msg = None
		
		self.responses = None
		self.counter_offers = None
		self.partners = None
	
	@stg.Entry_Stage('offer')
	def update_offer(self, C, player, action):
		
		assert_(action is not None, 'trade phase should always have an action')
		
		cmd, *rest = action
		
		if cmd == 'cancel':
			C.log[self.player].write('You cancel the trade')
			C.log.dindent()
			raise PhaseComplete
		
		if self.maritime is not None:
			num, res = rest
			self.offer[res] = num
			self.maritime_msg = num, res
			raise stg.Switch('maritime')
		
		if cmd == 'submit':
			
			C.log[self.player].write('Asking other players for response.')
			self.responses = tdict({p: None for p in C.players if p != self.player})
			self.counter_offers = tdict()
			for p in self.responses:
				self.display_trade(C.log[p], self.player, self.offer, self.demand)
			
			raise stg.Switch('counter')
		
		C.log[player].writef('You {} a {}', cmd, rest[0])
		self[cmd][rest[0]] += 1
		
		raise stg.Decide('propose')

	@staticmethod
	def display_trade(log, player, offer, demand, counter=False):
		offer_res = sum(([res] * num for res, num in offer.items()), [])
		demand_res = sum(([res] * num for res, num in demand.items()), [])
		
		if counter: # switch
			offer_res, demand_res = demand_res, offer_res
		
		log.writef('{} proposes a {}trade:', player, 'counter-' if counter else '')
		log.iindent()
		log.writef('Offering: {}', ', '.join(offer_res) if len(offer_res) else '-nothing-')
		log.writef('Demanding: {}', ', '.join(demand_res) if len(demand_res) else '-nothing-')
		log.dindent()
	
	@stg.Decision('propose', ['cancel', 'submit', 'trade'])
	def get_offer(self, C):
		
		offer, demand = self.offer, self.demand
		out = GameActions('You are proposing a trade')
		
		with out('cancel', 'Cancel trade'):
			out.add('cancel')
		
		with out('submit', 'Submit trade'):
			out.add('submit')
		
		with out('trade', 'Change trade'):
			out.add('demand', tset(res for res in demand))
			out.add('offer', tset(res for res, num in self.player.resources.items() if num - offer[res] > 0))
		
		# TODO: add trade to info
		
		return tdict({self.player: out})
	
	@stg.Stage('counter')
	def set_counter(self, C, player, action=None):
		
		if action is not None:
			cmd, *rest = action
			
			if cmd == 'reject':
				del self.responses[player]
			
			elif cmd == 'accept':
				self.responses[player] = 'accept'
			
			else:
				if player not in self.counter_offers:
					self.counter_offers[player] = tlist([self.offer.copy(), self.demand.copy()])
				
				res, = rest
				delta = -1 ** (cmd == 'demand')
				
				self.give(res, delta, *self.counter_offers[player])
			
			# check if some players havent responded yet
			for r in self.responses.values():
				if r is None:
					raise stg.Switch('commit')
		
		raise stg.Decide('counter')
	
	def give(self, res, delta, offers, demands):
		
		target, supply = offers, demands
		if delta < 0:
			target, supply = supply, target
		delta = abs(delta)
		
		if supply[res] > 0:  # remove supply first
			new = max(0, supply[res] - delta)
			delta += new - supply[res]
			supply[res] = new
		
		target[res] += delta
	
	@stg.Decision('counter', ['reject', 'accept', 'counter'])
	def get_counter(self, C):
		
		outs = tdict()
		
		for p, r in self.responses.items():
			if r is None:
				
				offer, demand = self.offer, self.demand
				status = 'Respond to trade'
				if p in self.counter_offers:
					offer, demand = self.counter_offers[p]
					status = 'Respond to trade with your counter-trade'
				
				out = GameActions(status)
				
				with out('reject', 'Reject trade'):
					out.add('reject')
				
				with out('accept', 'Accept {}trade'.format('counter-' if p in self.counter_offers else '')):
					if trade_available(p, demand):
						out.add('accept')
				
				if 'allow_counter_trades' not in C.state or C.state.allow_counter_trades:  # TODO: add this to config/settings
					with out('counter', 'Counter by amending the trade'):
						out.add('demand', tset(res for res in demand))
						out.add('offer', tset(res for res, num in p.resources.items() if num - offer[res] > 0))
				
				outs[p] = out
		
			# TODO: add trades to out.info for AIs
		
		return outs
	
	@stg.Stage('commit')
	def finalize(self, C, player, action=None):
		
		if len(self.responses):
			if action is None:
				
				accepts = tset()
				counters = tset()
				
				for p in self.responses:
					(counters if p in self.counter_offers else accepts).add(p)
				
				for c in counters:
					self.display_trade(C.log[self.player], c, *self.counter_offers[c], counter=True)
				
				raise stg.Decide('commit', accepts=accepts, counters=counters)
		
			cmd, = action
			
			if cmd in self.responses:
				offer, demand = self.offer, self.demand
				if cmd in self.counter_offers:
					C.log[self.player].writef('You accept {}\'s counter-trade', cmd)
					offer, demand = self.counter_offers[cmd]
				execute_trade(offer, demand, C.state.bank,
				              from_player=self.player, to_player=cmd,
				              log=C.log)
				
			else:
				C.log[self.player].write('You cancel the trade.')
		
		else:
			C.log[self.player].write('No one has accepted your trade offer.')
		
		C.log.dindent()
		raise PhaseComplete
		
	@stg.Decision('commit', ['cancel', 'accept', 'counter'])
	def final_decision(self, C, accepts, counters):
		
		status = 'No one has accepted your trade'
		if len(accepts) or len(counters):
			status = 'Players have responded to your trade'
		out = GameActions(status)
		
		with out('cancel', 'Cancel trade'):
			out.add('cancel')
		
		with out('accept', 'Accept trade with:'):
			if len(accepts):
				out.add(accepts)
		
		with out('counter', 'Accept counter-trade from:'):
			if len(counters):
				out.add(counters)
				
		# TODO: add trades to out.info for AIs
		
		return tdict({self.player: out})
	
	
	@stg.Stage('maritime')
	def set_maritime(self, C, player, action=None):
		
		if action is None:
			raise stg.Decide('maritime')
		
		res, = action
		
		if res != 'cancel':
			self.demand[res] = 1
			
			execute_trade(self.offer, self.demand, C.state.bank,
			              from_player=self.player, to_player=None,
			              log=C.log)
		
		C.log.dindent()
		raise PhaseComplete
	
	@stg.Decision('maritime', ['cancel', 'maritime-trade'])
	def get_maritime(self, C):
		out = GameActions('What resource would you like for {} {}'.format(*self.maritime_msg))
		
		with out('cancel', desc='Cancel trade'):
			out.add('cancel')
		
		with out('maritime-trade', desc='Select the resource to receive'):
			out.add(tset(self.demand.keys()))
		
		return tdict({self.player: out})