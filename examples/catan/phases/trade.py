import numpy as np
from gsm import GamePhase, GameActions, PhaseComplete
from gsm import tset, tdict, tlist
from gsm import writef, assert_

from gsm.common import stages as stg

from ..ops import trade_available, execute_trade


class TradePhase(stg.StagePhase):
	
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
		
		if cmd == 'send':
			
			C.log[self.player].write('Asking other players for response.')
			self.responses = tdict({p: None for p in C.players if p != self.player})
			self.counter_offers = tdict()
			offer_res = sum(([res] * num for res, num in self.offer.items()), [])
			demand_res = sum(([res] * num for res, num in self.demand.items()), [])
			for p in self.responses:
				C.log[p].writef('{} offers a trade:', self.player)
				C.log.iindent()
				C.log[p].writef('Paying: {}', ', '.join(offer_res) if len(offer_res) else '-nothing-')
				C.log[p].writef('Receiving: {}', ', '.join(demand_res) if len(demand_res) else '-nothing-')
				C.log.dindent()
			
			raise stg.Switch('counter')
	
	# TODO: update with offer/demand
	
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
						out.add('offer', tset(res for res, num in p.resources.items() if num > 0))
				
				outs[p] = out
		
		return outs
	
	@stg.Stage('commit')
	def finalize(self, C, player, action=None):
		
		if action is None:
			raise stg.Decide('commit')
		
		raise NotImplementedError
	
	@stg.Decision('commit', ['cancel', 'accept', 'counter'])
	def final_decision(self, C):
		raise NotImplementedError
	
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
	
	def execute(self, C, player=None, action=None):
		
		if action is None:
			raise Exception('No action to process')
		
		obj, *rest = action
		
		if obj == 'cancel':
			C.log[self.player].write('You cancel the trade')
			C.log.dindent()
			raise PhaseComplete
		
		if self.partners is not None:
			execute_trade(self.offer, self.demand, C.state.bank,
			              from_player=self.player, to_player=obj,
			              log=C.log)
			C.log.dindent()
			raise PhaseComplete
		
		if obj == 'accept' or obj == 'reject':
			
			self.responses[player] = obj == 'accept'
			
			# check if all responses have been collected
			self.partners = tset()
			for p, resp in self.responses.items():
				if resp:
					self.partners.add(p)
				elif resp is None:
					self.partners = None
					return
			self.responses = None
			
			if len(self.partners) == 0:
				C.log[self.player].write('No players accepted the trade')
				C.log.dindent()
				raise PhaseComplete
			return
		
		if self.maritime is not None:
			if obj == 'offer':
				num, res = rest
				self.offer[res] = num
				self.maritime_msg = num, res
			else:
				res = obj
				self.demand[res] = 1
				
				execute_trade(self.offer, self.demand, C.state.bank,
				              from_player=self.player, to_player=None,
				              log=C.log)
				C.log.dindent()
				raise PhaseComplete
		
		else:  # domestic trade
			if obj == 'send':
				C.log[player].write('Asking other players for response.')
				self.responses = tdict({p: None for p in C.players if p != self.player})
				offer_res = sum(([res] * num for res, num in self.offer.items()), [])
				demand_res = sum(([res] * num for res, num in self.demand.items()), [])
				for p in self.responses:
					C.log[p].writef('{} offers a trade:', self.player)
					C.log.iindent()
					C.log[p].writef('Paying: {}', ', '.join(offer_res) if len(offer_res) else '-nothing-')
					C.log[p].writef('Receiving: {}', ', '.join(demand_res) if len(demand_res) else '-nothing-')
					C.log.dindent()
			else:
				C.log[player].writef('You {} a {}', obj, rest[0])
				self[obj][rest[0]] += 1
	
	def encode(self, C):
		
		if self.maritime is not None:
			out = GameActions('What resource would you like for {} {}'.format(*self.maritime_msg))
			
			with out('cancel', desc='Cancel trade'):
				out.add('cancel')
			
			with out('maritime-trade', desc='Select the resource to receive'):
				out.add(tset(self.demand.keys()))
			
			return tdict({self.player: out})
		
		if self.partners is not None:
			out = GameActions('Some players accepted your offer')
			
			with out('cancel', desc='Cancel trade'):
				out.add('cancel')
			
			with out('domestic-confirm', desc='Select player to confirm trade'):
				out.add(self.partners)
			
			return tdict({self.player: out})
		
		if self.responses is not None:
			outs = tdict()
			for p, resp in self.responses.items():
				if resp is None:
					out = GameActions(writef('Do you accept the trade proposed by {}.', self.player))
					out.info.offer = self.offer
					out.info.demand = self.demand
					with out('domestic-response', desc='Choose to accept or reject trade'):
						if trade_available(p, self.demand):
							out.add('accept')
						out.add('reject')
					outs[p] = out
			return outs
		
		out = GameActions('Choose what resources to trade')
		
		with out('cancel', desc='Cancel trade'):
			out.add('cancel')
		
		with out('send', desc='Send trade offer to opponents'):
			out.add('send')
		
		with out('domestic-trade', desc='Domestic Trade (with players)'):
			out.add('demand', tset(res for res in self.player.resources))
			if self.player.num_res:
				out.add('offer', tset(res for res, num in self.player.resources.items() if num > 0))
		
		return tdict({self.player: out})
