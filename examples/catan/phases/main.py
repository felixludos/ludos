
import numpy as np
from gsm import GamePhase, GameActions, GameObject
from gsm.common import TurnPhase
from gsm import tset, tdict, tlist
from gsm import PhaseInterrupt, PhaseComplete

from ..ops import build, unbuild, roll_dice, get_knight, gain_res, check_building_options, bank_trade_options, update_stats

class MainPhase(TurnPhase):
	
	def __init__(self, player):
		super().__init__(player=player)
		
		self.roll = None
		
		self.devcard = None
		self.card_info = None # for processing multi decision devcards
		
		self.pre_check = True
	
	def execute(self, C, player=None, action=None):
		
		if action is None:
			if len(player.devcards):
				self.devcard = get_knight(player.devcards)
				return
			else:
				self.pre_check = False
		
		if self.roll is None and not self.pre_check:
			
			self.roll = roll_dice(C.RNG)
			
			C.log.zindent()
			C.log.writef('{} rolled: {}.', player, self.roll)
			C.log.iindent()
			
			if self.roll == 7:
				C.phase_stack.append(C.create_phase('main', C.state.turns))
				raise PhaseInterrupt('robber', stack=False)
		
			hexes = C.state.numbers[self.roll]
			for hex in hexes:
				if hex != C.state.robber.loc:
					for c in hex.corners:
						if 'building' in c and c.building.obj_type in C.state.production:
							gain = C.state.production[c.building.obj_type]
							gain_res(hex.res, C.state.bank, c.building.player, gain, C.log)
			
			for player in C.players.values():
				update_stats(player)
		
			return
		
		obj, *rest = action
		
		if obj == 'pass':
			C.stack.push('main')
			raise PhaseComplete
		
		if obj == 'cancel':
			if self.devcard is not None and self.devcard.name == 'Road Building':
				unbuild(C, self.card_info.building)
			self.devcard = None
			self.card_info = None
		
		if obj == 'confirm':
			self.devcard = None
			self.card_info = None
			return
			
		# trade
		if obj in {'maritime', 'offer', 'demand'}:
			raise PhaseInterrupt('trade', transfer=True)
		
		if self.devcard is not None:
			if self.devcard.name == 'Knight':
				raise NotImplementedError
			elif self.devcard.name == 'Road Building':
				if self.card_info is None:
					build(C, 'road', player, obj)
					self.card_info = obj
					
				else:
					build(C, 'road', player, obj)
					self.devcard = None
					self.card_info = None
					
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
				elif obj.name == 'Monopoly':
					res, = rest
					C.log.writef('{} plays Monopoly, claiming all {}', player, res)
					for opp in C.players.values():
						if opp != player and opp.resources[res] > 0:
							player.resources[res] += opp.resources[res]
							C.log.writef('{} receives {} {} from {}', player, opp.resources[res], res, opp)
				elif obj.name == 'Year of Plenty':
					res, = rest
					if self.card_info is None:
						self.devcard = obj
						self.card_info = res
					else:
						C.log.writef('{} plays {}, and receives: {} and {}',
						             player, self.devcard, self.card_info, res)
						gain_res(self.card_info, C.state.bank, player, 1, log=C.log)
						gain_res(res, C.state.bank, player, 1, log=C.log)
						self.card_info = None
						self.devcard = None
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
		
		out = GameActions()
		
		out.begin()
		out.add('pass')
		out.write('End your turn')
		out.commit()
		
		if self.pre_check:
			self.pre_check = False
			out.begin()
			if self.devcard is not None:
				out.add(self.devcard)
				out.add('cancel')
				out.status.write('Before rolling, you can play your knight')
			else:
				out.add('confirm')
				out.status.write('Confirm your turn beginning')
			out.commit()
			return tdict({self.player.name:out})

		if self.devcard is not None:
			
			if self.devcard.name == 'Knight':
				out.begin()
				if self.card_info is None:
					
					options = tset(f for f in C.state.world.fields if 'robber' not in f)
					out.add(options)
					out.add('cancel')
					out.status.write('Choose where to move the knight.')
				else:
					# identify players in loc
					opps = tset(c.building.player for c in self.card_info.corners
					            if 'building' in c and c.building.player != self.player)
					out.add(opps)
					out.add('cancel')
					out.status.write('Choose what player to steal from.')
					
				out.commit()
		# building
		options = check_building_options(self.player, C.state.costs, C.state.dev_deck)
		for bldname, opts in options.items():
			out.begin()
			out.write(C.state.msgs.build[bldname])
			out.add(opts)
			out.commit()
		
		# trading
		options = bank_trade_options(self.player, C.state.bank_trading)
		if len(options):
			out.begin()
			out.add('maritime', 'offer', tset((num, res) for res,num in options.items()))
			out.write('Maritime Trade (with the bank)')
			out.commit()
		
		out.begin()
		out.add('demand', tset(res for res in self.player.resources))
		if self.player.num_res:
			out.add('offer', tset(res for res, num in self.player.resources.items() if num > 0))
		out.write('Domestic Trade (with players)')
		out.commit()
		
		# play dev card
		if self.player.num_dev: # TODO: make sure you cant play devcards bought this turn
			out.begin()
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
			out.write('Play a development card')
			out.commit()
		
		out.status.writef('You rolled: {}', self.roll)
		
		return tdict({self.player.name:out})


