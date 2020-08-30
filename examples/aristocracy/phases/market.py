
import numpy as np
from ludos import GameOver, GamePhase, GameActions, GameObject
from ludos import gset, gdict, glist
from ludos import SwitchPhase, PhaseComplete, SubPhase

from ludos.common import TurnPhase
from ludos.common import stages as stg
from ludos.common import Selection

from ..ops import get_next_market
from ludos import util

class MarketPhase(stg.StagePhase, game='aristocracy', name='market'):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
	
		self.royal_actions = {'king':'build', 'queen':'visit', 'jack':'buy'}
	
	@stg.Entry_Stage('select')
	def select_stand(self, C, player, action=None):
		
		if action is None:
			players = glist(p for p in C.players if len(p.hand))
			
			if len(players) == 0:
				raise PhaseComplete
			
			self.sel = Selection(players, log=C.log,
			                     option_fn=lambda p: p.hand,
			                     status='You may choose cards for your market stand.')
			
		else:
			stands = self.sel.step(player, action)
			if stands is not None:
				for p, stand in stands.items():
					if len(stand):
						self.done = gset()
						for p, stand in stands.items():
							p.market.update(stand)
							C.log.writef('{}\'s stand contains: {}', p, ', '.join(str(card) for card in stand))
							for card in stand:
								p.hand.remove(card)
								card.visible.update(C.players)
						
						raise stg.Switch('prep')
					
				raise PhaseComplete
			
		raise stg.Decide('select')
		
	@stg.Decision('select', ['complete', 'select', 'deselect'])
	def choose_stand(self, C):
		return self.sel.options()
	
	@stg.Stage('prep')
	def prep_market(self, C, player, action=None):
		
		self.active = self._find_next(C.players)
		
		if self.active is None:
			# C.log.write('Market phase complete')
			raise stg.Switch('cleanup')
		
		self.actions = len(self.active.market)
		self.done.add(self.active)
		
		raise stg.Switch('main')
	
	def _find_next(self, players):
		
		mn = None
		options = gset()
		
		# check order of available players with markets
		for player in players:
			if player not in self.done and len(player.marker):
				total = sum(card.value for card in player.market)
				if mn is None and mn > total:
					options.clear()
					options.add(player)
				elif mn == total:
					options.add(player)
			
		if len(options) == 1:
			return options.pop()
			
		# tie break with herald order
		mn = None
		best = None
		
		for player in options:
			if mn is None or player.order < mn:
				mn, best = player.order, player
		
		return best

	@stg.Stage('main', switch=['visit', 'buy'])
	def main_market(self, C, player, action=None):
		
		if action is not None:
			
			cmd, = action
			
			if cmd == 'pass':
				self.actions -= 1
			
			elif action.obj_type == 'royal':
				self.cost = None
				if cmd == 'build':
					raise SubPhase('build', player=player, cost=self.cost)
				raise stg.Switch(cmd)
			
			elif action.obj_type == 'trade':
				raise stg.Switch('trade', send_action=True)
			
			elif action.obj_type == 'sell':
				raise stg.Switch('sell', send_action=True)
			
			elif action.obj_type == 'favor':
				self.cost = cmd
				typ = self.royal_actions[cmd._royal]
				if typ == 'build':
					raise SubPhase('build', player=player, cost=self.cost)
				raise stg.Switch(typ)
		
		if self.actions == 0:
			raise stg.Switch('prep')
		else:
			C.log.writef('{} has {} actions remaining', player, self.actions)
		
		raise stg.Decide('action')
		
	@stg.Decision('action')
	def choose_actions(self, C):
		
		player = self.active
		
		out = GameActions('You have {} action{} remaining'.format(self.actions, 's' if self.actions > 1 else ''))
		
		with out('pass', 'Pass action'):
			out.add('pass')
		
		with out('trade', 'Trade in the market'):
			my, other = self._get_trade_options(C, player)
			out.add(my)
			out.add(other)
		
		with out('hide', 'Hide a card from your stand'):
			out.add(player.market)
		
		with out('sell', 'Sell 2 of our cards for a coin'):
			if len(player.market) >= 2:
				out.add(player.market)
		
		with out('favor', 'Use a royal as a favor'):
			out.add(card for card in player.market if card.isroyal())
			out.add(card for card in player.hand if card.isroyal())
			
		with out('royal', 'Pay 1 coin to take the royal action'):
			if player.money > 0:
				out.add(self.royal_actions[self.royal])
		
		with out('store', 'Store a card in your building'):
			for name, buildings in player.buildings.items():
				for bld in buildings:
					out.add(bld.storage)
		
		with out('downgrade', 'Pick up a card from one of your buildings'):
			for name, buildings in player.buildings.items():
				if name != 'farm':
					for bld in buildings:
						out.add(bld.storage)
		
		return gdict({player: out})
	
	def _get_trade_options(self, C, player):
		my = gset(player.market)
		other = gset(C.state.market.neutral)
		for p in C.players:
			if p != player:
				other.update(p.market)
		return my, other
	
	@stg.Stage('trade')
	def trade_cards(self, C, player, action=None):
		
		card, = action
		
		if card == 'cancel':
			if 'trade_offer' in self:
				del self.trade_offer
			if 'trade_demand' in self:
				del self.trade_demand
			
			C.log[player].write('You canceled the trade.')
			
			raise stg.Switch('main')
		
		if 'trade_offer' in self:
			self.trade_demand = card
		elif 'trade_demand' in self:
			self.trade_offer = card
		else: # find out where to store this selection
			my, other = self._get_trade_options(C, player)
			
			if card in my:
				self.trade_offer = card
			elif card in other:
				self.trade_demand = card
			else:
				raise Exception('Error: invalid trade')
	
		if 'trade_offer' not in self or 'trade_demand' not in self:
			raise stg.Decide('trade')
		
		# execute trade
		
		src = C.state.market.neutral
		if self.trade_demand not in src:
			for p in C.players:
				if p != player and self.trade_demand in p.market:
					src = p.market
		
		src.remove(self.trade_demand)
		player.market.add(self.trade_demand)
		
		player.market.remove(self.trade_offer)
		src.add(self.trade_offer)
		
		C.log.writef('{} trades {} and {}'.format(player, self.trade_offer, self.trade_demand))
		del self.trade_offer
		del self.trade_demand
		
		self.actions -= 1
		raise stg.Switch('main')
	
	
	@stg.Decision('trade', ['cancel', 'trade'])
	def trade_options(self, C):
		out = GameActions('Choose a second card to trade with')
		
		with out('cancel', 'Cancel trade'):
			out.add('cancel')
		
		with out('trade', 'Complete trade'):
			my, other = self._get_trade_options(C, self.active)
			if 'trade_demand' in self:
				out.add(my)
			if 'trade_offer' in self:
				out.add(other)
				
		return gdict({self.active:out})
	
		
	@stg.Stage('sell')
	def sell_cards(self, C, player, action=None):
		
		card, = action
		
		if card == 'cancel':
			if 'pick' in self:
				del self.pick
			
			C.log[player].write('You cancel the sale.')
		
		elif 'pick' in self:
			
			player.market.remove(self.pick)
			player.market.remove(card)
			
			player.money += 1
			
			C.log.writef('{} sells {} and {} for a coin.', player, self.pick, card)
			
			self.actions -= 1
			
		else:
			self.pick = card
			raise stg.Decide('sell')
		
		raise stg.Switch('main')
	
	@stg.Decision('sell', ['cancel', 'sell'])
	def sell_options(self, C):
		out = GameActions('Choose a second card to sell')
		
		with out('cancel', 'Cancel sell'):
			out.add('cancel')
		
		with out('sell', 'Complete sale'):
			out.add(self.active.market - gset(self.pick))
			
		return gdict({self.active:out})
	
	@stg.Stage('cleanup')
	def cleanup_market(self, C, player, action=None):
		
		for p in C.players:
			for card in p.market:
				card.visible.clear()
				card.visible.add(p)
				p.hand.add(card)
			p.market.clear()
		
		raise PhaseComplete
	
	@stg.Stage('build')
	def build_action(self, C, player, action=None):
		
		if action is None:
			raise stg.Decide('build')
		
		cmd, = action
		
		
		
		self.actions -= 1
		raise stg.Switch('main')
	
	@stg.Decision('build', ['cancel', 'create', 'upgrade'])
	def build_choices(self, C):
		
		out = GameActions('Select what to build or upgrade')
		
		with out('cancel', 'Cancel build'):
			out.add('cancel')
			
		available = len(self.active.hand) + len(self.active.market) - int(self.cost is not None)
		
		with out('create', 'Create new building'):
			for name, count in C.config.rules.counts.items():
				if available >= count:
					out.add(name)
		
		with out('upgrade', 'Upgrade one of your buildings'):
			if available:
				for bld, options in self.active.buildings.items():
					if bld != 'palace' and len(options):
						out.add(options)
		
		return gdict({self.active: out})
	
	@stg.Stage('visit')
	def visit_action(self, C, player, action=None):
		
		self.actions -= 1
		raise stg.Switch('main')
	
	@stg.Stage('buy')
	def buy_action(self, C, player, action=None):
		
		self.actions -= 1
		raise stg.Switch('main')