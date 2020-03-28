
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import SwitchPhase, PhaseComplete

from gsm.common import TurnPhase
from gsm.common import stages as stg
from gsm.common import Selection

from ..ops import get_next_market
from gsm import util

class MarketPhase(stg.StagePhase, game='aristocracy', name='market'):
	
	@stg.Entry_Stage('select')
	def select_stand(self, C, player, action=None):
		
		if action is None:
			players = tlist(p for p in C.players if len(p.hand))
			
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
						self.done = tset()
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
		options = tset()
		
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

	@stg.Stage('main', switch=['king', 'queen', 'jack'])
	def main_market(self, C, player, action=None):
		
		if action is not None:
			
			cmd, = action
			
			if cmd == 'pass':
				pass
			
			elif cmd == 'royal':
				raise NotImplementedError
			
			elif action.obj_type == 'trade':
				raise stg.Switch('trade', send_action=True)
			
			elif action.obj_type == 'sell':
				raise stg.Switch('sell', send_action=True)
			
			elif action.obj_type == 'favor':
				raise stg.Switch(cmd._royal)
		
		raise stg.Decide('action')
		
	@stg.Decision('action')
	def choose_actions(self, C):
		
		player = self.active
		
		out = GameActions('You have {} action{} remaining'.format(self.actions, 's' if self.actions > 1 else ''))
		
		with out('pass', 'Pass action'):
			out.add('pass')
		
		with out('trade', 'Trade in the market'):
			out.add(player.market)
			out.add(C.state.market.neutral)
			for p in C.players:
				if p != player and len(p.market):
					out.add(p.market)
		
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
				out.add('royal')
		
		with out('store', 'Store a card in your building'):
			for name, buildings in player.buildings.items():
				for bld in buildings:
					out.add(bld.storage)
		
		with out('downgrade', 'Pick up a card from one of your buildings'):
			for name, buildings in player.buildings.items():
				if name != 'farm':
					for bld in buildings:
						out.add(bld.storage)
		
		return tdict({player: out})