
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import PhaseComplete, SwitchPhase

from ..ops import satisfies_vic_req, get_next_market

class RoyalPhase(GamePhase):
	
	def execute(self, C, player=None, action=None):
		
		if 'pre_complete' not in self:
			C.log.writef('{} phase begins', self.name.capitalize())
			C.log.iindent()
			self.pre_complete = True
			
			self.sel = tdict({p:tset() for p in C.players})
			self.active = tset(C.players)
			
			# create neutral market
			num = C.config.rules.neutral_market[self.name]
			if num > 0:
				cards = C.state.deck.draw(num)
				
			# draw cards
			num = C.config.rules.draw_cards
			if num > 0:
				C.log.write('Everybody draws {} card{}'.format(num, 's' if num > 1 else ''))
				for p in C.players:
					cards = C.state.deck.draw(num, player=player)
					C.log[p].writef('You draw: {}'.format(', '.join(['{}']*num)), *cards)
					p.hand.add(cards)
			
			self.pre(C)
		
		if action is not None:
			obj, = action
			
			if 'ready' == obj:
				self.active.remove(player)
				if len(self.active) == 0:
					self.market_complete = True
					
					nxt = get_next_market(self.sel)
					if nxt is not None:
						for p, cards in self.sel:
							for card in cards:
								p.hand.remove(card)
							p.market = cards
						
						raise SwitchPhase('market', player=nxt, market=self.sel)
					else:
						C.log.write('No one goes to the market')
						
			elif obj in self.sel[player]:
				C.log[player].iindent()
				C.log[player].writef('You unselect {}', obj)
				C.log[player].dindent()
				self.sel[player].remove(obj)
			else:
				C.log[player].iindent()
				C.log[player].writef('You select {}', obj)
				C.log[player].dindent()
				self.sel[player].add(obj)
			
		if 'market_complete' in self:
			self.post_complete = True
			self.post(C)
			
		if 'post_complete' in self:
			C.state.market.clear()
			if len(C.stack) == 0:
				C.stack.extend(C.state.royal_phases)
				C.log.zindent()
			raise PhaseComplete
		
	def pre(self, C):
		raise NotImplementedError
	
	def post(self, C):
		raise NotImplementedError
		
	def encode(self, C):
		
		full = tdict()
		
		for player in self.active:
			out = GameActions('Select what cards to bring to the market')
		
			with out('select', 'Select card'):
				opts = player.hand - self.sel[player]
				if len(opts):
					out.add(opts)
			
			with out('unselect', 'Unselect card'):
				if len(self.sel[player]):
					out.add(self.sel[player])
			
			with out('ready', 'Ready for the market'):
				out.add('ready')
		
			full[player] = out
		
		return full


class KingPhase(RoyalPhase):
	def pre(self, C):
		
		# increment herald
		for player in C.players:
			player.order += 1
			player.order %= len(C.players)
			if player.order == 0:
				C.state.herald = player
				C.log.writef('{} becomes herald', player)
		
		for player in C.players:
			if len(player.hand) > player.hand_limit:
				raise SwitchPhase('tax')
	
	def post(self, C):
		for player in C.players:
			if satisfies_vic_req(player, C.config.rules.victory_conditions):
				raise SwitchPhase('claim')
		

class QueenPhase(RoyalPhase):
	def pre(self, C):
		raise SwitchPhase('ball')
	
	def post(self, C):
		for player in C.players:
			income = len(player.buildings.estate) + len(player.buildings.palace)
			if income > 0:
				player.money += income
				C.log.writef('{} earns {} coins from their buildings', player, income)

class JackPhase(RoyalPhase):
	def pre(self, C):
		raise SwitchPhase('auction')
	
	def post(self, C):
		for player in C.players:
			for farm in player.buildings.farm:
				if farm.harvest is None:
					card = C.state.deck.draw()
					card.visible.clear()
					farm.harvest = card
					C.log.writef('{} is harvestable on {}\'s {}', card, player, farm)
		




		
