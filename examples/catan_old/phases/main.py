
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm.common import TurnPhase
from gsm import tset, tdict, tlist
from gsm import SwitchPhase, PhaseComplete

from ..ops import build, unbuild, play_dev, pay_cost, can_buy, roll_dice, check_victory, get_knight, gain_res, check_building_options, bank_trade_options

class MainPhase(TurnPhase):
	
	def __init__(self, player, **other):
		super().__init__(player=player, **other)
		
		self.roll = None
		
		self.devcard = None
		self.card_info = None # for processing multi decision devcards
		
		self.bought_devcards = tset()
		
		self.pre_check = 'check'
	
	def execute(self, C, player=None, action=None):
		
		if action is None:
			if self.pre_check == 'check':
				self.pre_check = get_knight(self.player.devcards) \
					if len(self.player.devcards) else None
			else: # coming back from robber or trade phase
				return
		elif action[0] == 'continue':
			self.pre_check = None

		if self.roll is None and self.pre_check is None:
			
			self.roll = roll_dice(C.RNG)
			if len(C.state.rolls):
				self.roll = C.state.rolls.pop()
			
			C.log.zindent()
			C.log.writef('{} rolled: {}.', self.player, self.roll)
			C.log.iindent()
			
			if self.roll == 7:
				C.stack.push('main')
				raise SwitchPhase('robber', send_action=False, stack=False,
				                  player=self.player)
		
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
			return
		
		if obj == 'continue':
			return
		
		# trade
		if obj == 'offer' or obj == 'demand':
			C.log[self.player].write('You start a trade')
			C.log.iindent()
			raise SwitchPhase('trade', send_action=True, stack=True,
			                  player=self.player,
			                  bank_trades=bank_trade_options(self.player, C.state.bank_trading)
			                        if 'maritime' in action.get_type() else None)
		
		if self.devcard is not None:
			if self.devcard.name == 'Road Building':
				if self.card_info is None:
					bld = build(C, 'road', self.player, obj)
					self.card_info = bld
				else:
					bld = build(C, 'road', self.player, obj)
					play_dev(self.player, self.devcard)
					C.log.writef('{} plays {}, and builds: {} and {}',
					             self.player, self.devcard, self.card_info, bld)
					self.devcard = None
					self.card_info = None
			elif self.devcard.name == 'Year of Plenty':
				res, = obj
				gain_res(self.card_info, C.state.bank, self.player, 1, log=C.log)
				gain_res(res, C.state.bank, player, 1, log=C.log)
				play_dev(self.player, self.devcard)
				C.log.writef('{} plays {}, and receives: {} and {}',
				             self.player, self.devcard, self.card_info, res)
				self.card_info = None
				self.devcard = None
			else:
				raise Exception('unknown dev card: {} {}'.format(self.devcard, self.devcard.name))
		
		
		obj_type = obj.get_type()
		
		if 'build' in action.get_type():
			if obj_type == 'settlement':
				unbuild(C, obj, silent=False)
				bld = build(C, 'city', self.player, obj.loc)
			else:
				bld = build(C, 'settlement' if obj_type=='Corner' else 'road', self.player, obj)
			
			pay_cost(self.player, C.state.costs[bld.get_type()], C.state.bank)
			
		elif obj_type == 'devcard':
			if obj.name == 'Victory Point':
				raise Exception('Shouldnt have played a Victory point card')
			elif obj.name == 'Knight':
				raise SwitchPhase('robber', send_action=False, stack=True,
				                  knight=obj, player=self.player)
			elif obj.name == 'Monopoly':
				res, = rest
				for opp in C.players.values():
					if opp != self.player and opp.resources[res] > 0:
						self.player.resources[res] += opp.resources[res]
						C.log.writef('{} receives {} {} from {}', self.player, opp.resources[res], res, opp)
				C.log.writef('{} plays {}, claiming all {}', self.player, obj, res)
				play_dev(self.player, obj)
			
			elif obj.name == 'Year of Plenty':
				res, = rest
				self.devcard = obj
				self.card_info = res
			elif obj.name == 'Road Building':
				self.devcard = obj
			else:
				raise Exception('unknown card: {} {}'.format(obj, obj.name))
				
		elif obj_type == 'devdeck':
			card = C.state.dev_deck.draw()
			self.player.devcards.add(card)
			self.bought_devcards.add(card)
			C.log.writef('{} buys a development card', self.player)
			
			msg = ''
			if card.name == 'Victory Point':
				msg = ' (gaining 1 victory point)'
				self.player.vps += 1
			
			C.log[self.player].writef('You got a {}{}', card, msg)
			
			pay_cost(self.player, C.state.costs.devcard, C.state.bank)
		else:
			raise Exception('Unknown obj {}: {}'.format(type(obj), obj))

		if check_victory(C):
			raise GameOver

	def encode(self, C):
		
		out = GameActions('You rolled: {}. Take your turn.'.format(self.roll))
		
		if self.pre_check is not None:
			with out(name='pre'):
				if self.pre_check is not None:
					out.add(self.pre_check)
					self.pre_check = None
					out.set_status('Before rolling, you can play your knight or continue')
				else: # to avoid side info leak from lack of decision when having dev cards
					out.set_status('Confirm your turn beginning')
				
				out.add('continue')
				
				return tdict({self.player:out})
		
		if self.devcard is not None:
			with out('cancel', desc='Undo playing dev card'):
				out.add('cancel')
			
			if self.devcard.name == 'Road Building':
				options = check_building_options(self.player, C.state.costs)
				with out('dev-road', C.state.msgs.build.road):
					out.add(options.road)
			elif self.devcard.name == 'Year of Plenty':
				with out('dev-res', desc='Select a second resource'):
					out.add(tset(self.player.resources.keys()))
		else:
			# end turn
			with out(name='pass', desc='End your turn'):
				out.add('pass')
			
			# building
			options = check_building_options(self.player, C.state.costs)
			for bldname, opts in options.items():
				with out('build-{}'.format(bldname), C.state.msgs.build[bldname]):
					out.add(opts)
			
			# buy dev card
			if len(C.state.dev_deck) and can_buy(self.player, C.state.costs.devcard):
				with out('buy', desc='Buy a development card'):
					out.add(C.state.dev_deck)
			
			# trading
			with out('maritime-trade', desc='Maritime Trade (with the bank)'):
				options = bank_trade_options(self.player, C.state.bank_trading)
				if len(options):
					out.add('offer', tset((num, res) for res,num in options.items()))
			
			with out('domestic-trade', desc='Domestic Trade (with players)'):
				out.add('demand', tset(res for res in self.player.resources))
				if self.player.num_res:
					out.add('offer', tset(res for res, num in self.player.resources.items() if num > 0))
			
			# play dev card
			with out('play', desc='Play a development card'):
				if len(self.player.devcards):
					res = tset(self.player.resources.keys())
					for card in self.player.devcards:
						if card in self.bought_devcards:
							pass
						elif card.name == 'Monopoly':
							out.add(card, res)
						elif card.name == 'Year of Plenty':
							out.add(card, res)
						elif card.name == 'Victory Point':
							pass
						else:
							out.add(card)
					
		
		return tdict({self.player:out})


