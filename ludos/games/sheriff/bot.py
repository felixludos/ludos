import random

import discord
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event, as_loop



@fig.component('sheriff-bot')
class SheriffBot(DiscordBot):
	
	_initial_money = 50
	
	_config_bank_resource_counts = {
		3: {
			'apples': 48,
			'cheese': 36,
			'bread': 0,
			'chicken': 24,
			
			'pepper': 18,
			'mead': 16,
			'silk': 9,
			'crossbow': 5,
			
			'green apples': 2,
			'golden apples': 1,
			'gouda cheese': 2,
			'bleu cheese': 0,
			'rye bread': 0,
			'pumpernickel bread': 0,
			'royal rooster': 1,
		},
		4: {
			'apples': 48,
			'cheese': 36,
			'bread': 36,
			'chicken': 24,
			
			'pepper': 22,
			'mead': 21,
			'silk': 12,
			'crossbow': 5,
			
			'green apples': 2,
			'golden apples': 2,
			'gouda cheese': 2,
			'bleu cheese': 1,
			'rye bread': 3,
			'pumpernickel bread': 1,
			'royal rooster': 2,
		},
	}
	_config_bank_resource_counts[5] = _config_bank_resource_counts[4]

	_bank_resource_value = {
		'apples': 2,
		'cheese': 3,
		'bread': 3,
		'chicken': 4,
		
		'pepper': 6,
		'mead': 7,
		'silk': 8,
		'crossbow': 9,
		
		'green apples': 4,
		'golden apples': 6,
		'gouda cheese': 6,
		'bleu cheese': 9,
		'rye bread': 6,
		'pumpernickel bread': 9,
		'royal rooster': 8,
	}
	
	_bank_resource_costs = {
		'apples': 2,
		'cheese': 2,
		'bread': 2,
		'chicken': 2,
		
		'pepper': 4,
		'mead': 4,
		'silk': 4,
		'crossbow': 4,
		
		'green apples': 3,
		'golden apples': 4,
		'gouda cheese': 4,
		'bleu cheese': 5,
		'rye bread': 4,
		'pumpernickel bread': 5,
		'royal rooster': 4,
	}
	
	
	_bank_bonus_info = {
		'green apples': 'counts as 2 apples',
		'golden apples': 'counts as 3 apples',
		'gouda cheese': 'counts as 2 cheese',
		'bleu cheese': 'counts as 3 cheese',
		'rye bread': 'counts as 2 bread',
		'pumpernickel bread': 'counts as 3 bread',
		'royal rooster': 'counts as 2 chicken',
	}
	
	
	async def _start_game(self):
		num = len(self.players)
		if num not in self._config_bank_resource_counts:
			# await self.table.send(f'Wrong number of players: {num}')
			# return
			num = 5
		
		self.resource_counts = self._config_bank_resource_counts[num]
		self.time_limit = max(3, num - 1)
		
		random.shuffle(self.players)
		await self.table.send('Player order: {}.'.format(', '.join(p.display_name for p in self.players)))
		self._remaining_rounds = len(self.players)
		await self.table.send(f'There will be {self._remaining_rounds} rounds.')
		
		self.sheriff = None
		self.money = {player: self._initial_money for player in self.players}
		self.stalls = {player: {} for player in self.players}
		self.hands = {player: [] for player in self.players}
	
		self.deck = [resource for resource, N in self.resource_counts.items() for _ in range(N)]
		random.shuffle(self.deck)
		
		await self._start_round()
		
		
	@as_loop(minutes=1)
	async def sheriff_timer(self):
		if self.sheriff_timer.current_loop == self.time_limit:
			await self.table.send(f'{self.guild.default_role}: **Time is up!**')
			self.sheriff_timer.stop()
			await self._resolve_round()
		elif self.sheriff_timer.current_loop == 0:
			await self.table.send(f'The sheriff {self.sheriff.display_name} has {self.time_limit} minutes to '
			                      f'decide which merchants to inspect. The timer starts **now**!')
		elif self.time_limit - self.sheriff_timer.current_loop == 1:
			await self.table.send(f'{self.guild.default_role}: **1 minute remaining!**')
		else:
			await self.table.send(f'{self.time_limit - self.sheriff_timer.current_loop} minutes remaining!')
		
		
	async def _start_round(self):
		if self._remaining_rounds == 0:
			await self._end_game()
		self._remaining_rounds -= 1
		await self._deal_cards()
		await self._assign_sheriff()
		
		await self._prep_trade_cards()

		# await self._prep_round()
		# self.sheriff_timer.start()
		
	
	async def _prep_trade_cards(self):
		self._status = 'Waiting for {} to replace cards'.format(', '.join(p.display_name for p in self.merchants))
		
		for player in self.merchants:
			comm = self.interfaces[player]
			hand = self.hands[player]
			
			msg = await comm.send(f'{player.mention} You may choose which of your cards to replace.')
			await self.register_reaction_query(msg, self._replace_cards,
			                                   *self._number_emojis[1:len(hand)], self._accept_mark)
	
	
	async def _replace_cards(self, reaction, user):
		
		if reaction.emoji == self._accept_mark:
			
			raise NotImplementedError
		
		pass
		
	
	async def _end_game(self):
		await self.table.send('Game over.')
	
	
	async def _deal_cards(self):
		bonus = lambda info: '' if info is None else f' - {info}'
		for player, hand in self.hands.items():
			hand.extend(self.deck.pop() for _ in range(max(0, 6-len(hand))))
			await self.interfaces[player].send(
				'Your hand:{}'.format('\n  - '.join(['', *[f'{res} (v: {self._bank_resource_value[res]}, '
				                                           f'c: {self._bank_resource_costs[res]})'
				                                           f'{bonus(self._bank_bonus_info.get(res,None))}'
				                                    for res in sorted(hand)]])))
	
	
	async def _assign_sheriff(self):
		if self.sheriff is None:
			self.sheriff = random.choice(self.players)
			# self.sheriff = self.players[0]
		else:
			idx = self.players.index(self.sheriff)
			idx = (idx+1)%len(self.players)
			self.sheriff = self.players[idx]
		
		await self.table.send(f'The sheriff is now {self.sheriff.mention}')
		
		self.merchants = [player for player in self.players if player != self.sheriff]
		
		
	
	
	




