
import numpy as np
from ludos import GameOver, GamePhase, GameActions, GameObject
from ludos.common import TurnPhase
from ludos.common import stages as stg
from ludos import gset, gdict, glist, assert_
from ludos import SwitchPhase, PhaseComplete, SubPhase

from ..ops import build, unbuild, play_dev, pay_cost, can_buy, roll_dice, check_victory, get_knight, gain_res, check_building_options, bank_trade_options

class MainPhase(TurnPhase, stg.StagePhase, name='main', game='catan'):
	
	def __init__(self, player, **other): # TODO: make sure only one dev card can be played, and not the ones bought
		super().__init__(player=player, **other)
		
		self.roll = None
		
		self.devcard = None
		self.card_info = None # for processing multi decision devcards
		
		self.bought_devcards = gset()
	
	@stg.Entry_Stage('roll')
	def roll_dice(self, C, player, action=None):
		
		if action is not None:
			
			cmd, = action
			
			if cmd != 'continue':
				self.pre_check = 'played' # can't play another dev card this turn
				self.devcard = cmd
				raise SubPhase('robber', player=self.player, knight=cmd)
		
		
		elif 'pre_check' not in self:
			self.pre_check = 'done'
			self.devcard = get_knight(self.player.devcards)
			if self.devcard is not None: # knight available
				raise stg.Decide('pre-knight', knight=self.devcard)
		
		if self.devcard is not None: # coming back from playing a knight
			if self.devcard in self.player.devcards: # check if knight was actually played
				self.devcard = None
		
		self.roll = roll_dice(C.RNG)
		if len(C.state.rolls):
			self.roll = C.state.rolls.pop()
		
		# TODO: delay telling other players (info leak, pre-knight)
		C.log.zindent()
		C.log.writef('{} rolled: {}.', self.player, self.roll)
		C.log.iindent()
		
		if self.roll == 7:
			self.set_current_stage('main') # when coming back, go straight to main stage
			raise SubPhase('robber', player=self.player)
		
		hexes = C.state.numbers[self.roll]
		for hex in hexes:
			if hex != C.state.robber.loc:
				for c in hex.corners:
					if 'building' in c and c.building.obj_type in C.state.production:
						gain = C.state.production[c.building.obj_type]
						gain_res(hex.res, C.state.bank, c.building.player, gain, C.log)
		
		raise stg.Switch('main')
	
	@stg.Decision('pre-knight', ['continue', 'knight'])
	def get_preroll(self, C, knight):
		
		out = GameActions('You can play your knight before rolling')
		
		with out('continue', 'Continue with your turn'):
			out.add('continue')
			
		with out('knight', 'Play your knight'):
			out.add(knight)  # TODO: maybe allow user to pick which knight to use
		
		return tdict({self.player: out})
	
	# def null_op(self, x=1): # TESTING
	# 	if False:
	# 		raise PhaseComplete
	
	@stg.Stage('main')
	def main_turn(self, C, player, action=None):
		if action is None:
			raise stg.Decide('main')
		
		# self.null_op(2) # TESTING
		
		obj, *rest = action
		
		if obj == 'pass':
			raise SwitchPhase('main')
		
		if obj == 'offer' or obj == 'demand':
			C.log[self.player].write('You start a trade')
			C.log.iindent()
			raise SubPhase('trade', send_action=True, player=self.player,
			                  bank_trades=bank_trade_options(self.player, C.state.bank_trading)
			                        if 'maritime' in action.get_type() else None)
		
		obj_type = obj.get_type()
		
		if 'build' in action.get_type():
			if obj_type == 'settlement': # replace this settlement
				unbuild(C, obj, silent=False)
				bld = build(C, 'city', self.player, obj.loc)
			else:
				bld = build(C, 'settlement' if obj_type == 'Corner' else 'road', self.player, obj)
			
			pay_cost(self.player, C.state.costs[bld.get_type()], C.state.bank)
		
		elif obj_type == 'devcard':
			if obj.name == 'Victory Point':
				raise Exception('Shouldnt have played a Victory point card')
			elif obj.name == 'Knight':
				raise SubPhase('robber', send_action=False, knight=obj, player=self.player)
			elif obj.name == 'Monopoly':
				res, = rest
				for opp in C.players.values():
					if opp != self.player and opp.resources[res] > 0:
						self.player.resources[res] += opp.resources[res]
						C.log.writef('{} receives {} {} from {}', self.player, opp.resources[res], res, opp)
				C.log.writef('{} plays {}, claiming all {}', self.player, obj, res)
				play_dev(self.player, obj)
				self.devcard = obj
			
			elif obj.name == 'Year of Plenty':
				res, = rest
				self.devcard = obj
				raise stg.Switch('year-plenty', res=res)
			elif obj.name == 'Road Building':
				self.devcard = obj
				raise stg.Switch('road-building')
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
		
		raise stg.Decide('main')
		
	@stg.Decision('main', ['pass', 'build-settlement', 'build-road', 'build-city', 'buy',
	                       'maritime-trade', 'domestic-trade', 'play'])
	def get_main_turn(self, C):
		
		out = GameActions('You rolled: {}. Take your turn.'.format(self.roll))
		
		with out('pass', 'End your turn'):
			out.add('pass')
		
		options = check_building_options(self.player, C.state.costs)
		for bldname, opts in options.items():
			with out('build-{}'.format(bldname), C.state.msgs.build[bldname]):
				out.add(opts)
		
		if len(C.state.dev_deck) and can_buy(self.player, C.state.costs.devcard):
			with out('buy', desc='Buy a development card'):
				out.add(C.state.dev_deck)
		
		with out('maritime-trade', desc='Maritime Trade (with the bank)'):
			options = bank_trade_options(self.player, C.state.bank_trading)
			if len(options):
				out.add('offer', gset((num, res) for res, num in options.items()))
		
		with out('domestic-trade', desc='Domestic Trade (with players)'):
			out.add('demand', gset(res for res in self.player.resources))
			if self.player.num_res:
				out.add('offer', gset(res for res, num in self.player.resources.items() if num > 0))
		
		with out('play', desc='Play a development card'):
			if len(self.player.devcards) and self.devcard is None:
				res = gset(self.player.resources.keys())
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
		
		return tdict({self.player: out})
	
	@stg.Stage('road-building')
	def set_road_building(self, C, player, action=None):
		if action is not None:
			loc, = action
			
			if loc == 'cancel':
				if self.card_info is not None:
					unbuild(C, self.card_info.building)
				self.card_info = None
				self.devcard = None
				raise stg.Switch('main')
			
			if self.card_info is None:
				bld = build(C, 'road', self.player, loc)
				self.card_info = bld
			else:
				bld = build(C, 'road', self.player, loc)
				play_dev(self.player, self.devcard)
				C.log.writef('{} plays {}, and builds: {} and {}',
				             self.player, self.devcard, self.card_info, bld)
				self.card_info = None
				raise stg.Switch('main')
				
		raise stg.Decide('road-building')
	
	@stg.Decision('road-building', ['cancel', 'dev-road'])
	def get_road_building(self, C):
		
		out = GameActions('You activated Road Building, and can now build a second road')
		
		with out('cancel', desc='Undo playing dev card'):
			out.add('cancel')
		
		options = check_building_options(self.player, C.state.costs)
		with out('dev-road', C.state.msgs.build.road):
			out.add(options.road)
		
		return tdict({self.player: out})
	
	
	@stg.Stage('year-plenty')
	def set_year_of_plenty(self, C, player, action=None, res=None):
		if action is None:
			self.card_info = res
			raise stg.Decide('year-plenty')
		
		res, = action
		
		if res != 'cancel':
			gain_res(self.card_info, C.state.bank, self.player, 1, log=C.log)
			gain_res(res, C.state.bank, player, 1, log=C.log)
			C.log.writef('{} plays {}, and receives: {} and {}',
			             self.player, self.devcard, self.card_info, res)
			
			play_dev(self.player, self.devcard)
		else:
			self.devcard = None
			
		self.card_info = None
		raise stg.Switch('main')
	
	@stg.Decision('year-plenty', ['cancel', 'pick'])
	def get_year_of_plenty(self, C):
		
		out = GameActions('You activated Year of Plenty, choose a second resource to collect')
		
		with out('cancel', desc='Undo playing dev card'):
			out.add('cancel')
		
		with out('dev-res', desc='Select a second resource'):
			out.add(gset(self.player.resources.keys()))
		
		return tdict({self.player: out})

	
