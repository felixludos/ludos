
import numpy as np
from gsm import GamePhase, GameActions, GameObject
from gsm.common import TurnPhase
from gsm import tset, tdict, tlist
from gsm import SwitchPhase, PhaseComplete

from ..ops import build, unbuild, play_dev, roll_dice, get_knight, gain_res, check_building_options, bank_trade_options

class MainPhase(TurnPhase):
	
	def __init__(self, player):
		super().__init__(player=player)
		
		self.roll = None
		
		self.devcard = None
		self.card_info = None # for processing multi decision devcards
		
		self.pre_check = None
	
	def execute(self, C, player=None, action=None):
		
		if action is None:
			self.pre_check = get_knight(player.devcards) if len(player.devcards) else None

		if self.roll is None and self.pre_check is None:
			
			self.roll = roll_dice(C.RNG)
			
			C.log.zindent()
			C.log.writef('{} rolled: {}.', player, self.roll)
			C.log.iindent()
			
			if self.roll == 7:
				C.stack.push('main')
				raise SwitchPhase('robber', send_action=False, stack=False,
				                  hand_lim=True)
		
			hexes = C.state.numbers[self.roll]
			for hex in hexes:
				if hex != C.state.robber.loc:
					for c in hex.corners:
						if 'building' in c and c.building.obj_type in C.state.production:
							gain = C.state.production[c.building.obj_type]
							gain_res(hex.res, C.state.bank, c.building.player, gain, C.log)
		
			return
		
		obj, *rest = action
		
		if obj == 'pass':
			raise SwitchPhase('main', stack=False)
		
		if obj == 'cancel':
			if self.devcard is not None:
				if self.devcard.name == 'Road Building':
					unbuild(C, self.card_info.building)
			self.devcard = None
			self.card_info = None
		
		if obj == 'confirm':
			self.devcard = None
			self.card_info = None
			return
			
		# trade
		if obj in {'maritime', 'offer', 'demand'}:
			raise SwitchPhase('trade', send_action=True, stack=True)
		
		if self.devcard is not None:
			if self.devcard.name == 'Road Building':
				if self.card_info is None:
					build(C, 'road', player, obj)
					self.card_info = obj
				else:
					build(C, 'road', player, obj)
					play_dev(player, self.devcard)
					self.devcard = None
					self.card_info = None
			elif self.devcard.name == 'Year of Plenty':
				res, = obj
				C.log.writef('{} plays {}, and receives: {} and {}',
				             player, self.devcard, self.card_info, res)
				gain_res(self.card_info, C.state.bank, player, 1, log=C.log)
				gain_res(res, C.state.bank, player, 1, log=C.log)
				play_dev(player, self.devcard)
				self.card_info = None
				self.devcard = None
			else:
				pass
		
		if isinstance(obj, GameObject):
			obj_type = obj.get_type()
			
			if obj_type == 'Edge':
				build(C, 'road', player, obj)
				for res, num in C.state.costs.road.items():
					gain_res(res, C.state.bank, player, -num)
			elif obj_type == 'Corner':
				if 'building' in obj:
					build(C, 'city', player, obj) # TODO: unbuild settlement when upgrading
					for res, num in C.state.costs.city.items():
						gain_res(res, C.state.bank, player, -num)
				else:
					build(C, 'settlement', player, obj)
					for res, num in C.state.costs.settlement.items():
						gain_res(res, C.state.bank, player, -num)
			elif obj_type == 'devcard':
				obj.visible.update(C.players.names())
				if obj.name == 'Victory Point':
					raise Exception('Shouldnt have played a Victory point card')
				elif obj.name == 'Knight':
					raise SwitchPhase('robber', send_action=True, stack=True,
					                  hand_lim=False)
				elif obj.name == 'Monopoly':
					res, = rest
					C.log.writef('{} plays Monopoly, claiming all {}', player, res)
					for opp in C.players.values():
						if opp != player and opp.resources[res] > 0:
							player.resources[res] += opp.resources[res]
							C.log.writef('{} receives {} {} from {}', player, opp.resources[res], res, opp)
					
				elif obj.name == 'Year of Plenty':
					res, = rest
					self.devcard = obj
					self.card_info = res
				else:
					self.devcard = obj
					
			elif obj_type == 'devdeck':
				card = C.state.dev_deck.draw()
				self.player.devcards.add(card)
				C.log.writef('{} buys a development card', player)
				
				msg = ''
				if card.name == 'Victory Point':
					msg = ' (gaining 1 victory point)'
				
				C.log[player.name].writef('You got a {}{}', card, msg)
				player.vps += 1
				
				for res, num in C.state.costs.devcard.items():
					gain_res(res, C.state.bank, self.player, -num)
			else:
				raise Exception('Unknown obj {}: {}'.format(type(obj), obj))


	def encode(self, C):
		
		out = GameActions('You rolled: {}'.format(self.roll))
		
		with out(name='pre'):
			if self.pre_check is not None:
				if self.pre_check is not None:
					out.add(self.pre_check)
					self.pre_check = None
					out.add('cancel')
					out.set_status('Before rolling, you can play your knight')
				else:
					out.add('confirm')
					out.set_status('Confirm your turn beginning')
				
				return tdict({self.player.name:out})
		
		with out(name='pass', desc='End your turn'):
			out.add('pass')

		if self.devcard is not None:
			pass
			
		else:
			# building
			options = check_building_options(self.player, C.state.costs, C.state.dev_deck)
			for bldname, opts in options.items():
				with out(bldname,C.state.msgs.build[bldname]):
					out.add(opts)
			
			# trading
			options = bank_trade_options(self.player, C.state.bank_trading)
			if len(options):
				with out('maritime-trade', desc='Maritime Trade (with the bank)'):
					out.add('maritime', 'offer', tset((num, res) for res,num in options.items()))
				
			with out('domestic-trade', desc='Domestic Trade (with players)'):
				out.add('demand', tset(res for res in self.player.resources))
				if self.player.num_res:
					out.add('offer', tset(res for res, num in self.player.resources.items() if num > 0))
			
			# play dev card
			if len(self.player.devcards): # TODO: make sure you cant play devcards bought this turn
				with out('play-dev', desc='Play a development card'):
					res = tset(self.player.resources.keys())
					for card in self.player.devcards:
						if card.name == 'Monopoly':
							out.add(card, res)
						elif card.name == 'Year of Plenty':
							out.add(card, res)
						elif card.name == 'Victory Point':
							pass
						else:
							out.add(card)
		
		return tdict({self.player.name:out})


