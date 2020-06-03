
import numpy as np
from gsm import GameOver, GamePhase, GameActions, GameObject
from gsm import tset, tdict, tlist
from gsm import PhaseComplete, SwitchPhase
from gsm.common import stages as stg
from gsm.common import Selection
from gsm import util

from .royals import RoyalPhase


class QueenPhase(RoyalPhase, game='aristocracy', name='queen'):
	@stg.Stage('pre')
	def pre_phase(self, C, player, action=None):
		
		for p in C.players:
			if len(p.hand) > 0:
				raise stg.Switch('ball')
		
		raise stg.Switch('market')
	
	@stg.Stage('ball')
	def run_ball(self, C, player, action=None):
		
		if action is None:
			self.sel = Selection(tlist(p for p in C.players if len(p.hand)), log=C.log,
			                     option_fn=lambda p: p.hand,
			                     status='You may choose cards to attend the ball.')
		else:
			done = self.sel.step(player, action)
			if done is not None:
				
				# run ball
				ball = tlist(C.state.market)
				for p, sel in done:
					p.hand -= sel
					ball.extend(sel)
				
				C.RNG.shuffle(ball)
				C.log.writef('The ball features: {}'.format(', '.join(map(str, ball))))
				
				C.RNG.shuffle(ball)
				
				ball = tset(ball)
				for p, sel in done:
					for _ in range(len(sel)):
						card = ball.pop()
						card.visible.clear()
						card.visible.add(p)
						p.hand.add(card)
				C.state.market.clear()
				C.state.market.update(ball)
				for card in C.state.market:
					card.visible.update(C.players)
				
				raise stg.Switch('market', royal='queen')
			
		raise stg.Decide('ball')
		
	@stg.Decision('ball', ['complete', 'select', 'deselect'])
	def sel_ball(self, C):
		return self.sel.options()
		
	@stg.Stage('post')
	def post(self, C, player, action=None):
		for player in C.players:
			income = len(player.buildings.estate) + len(player.buildings.palace)
			if income > 0:
				player.money += income
				C.log.writef('{} earns {} from their buildings', player, util.format_quantity('coin', income))

		raise SwitchPhase('jack')
