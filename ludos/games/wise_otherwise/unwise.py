from pathlib import Path
import random
import discord

from omnibelt import load_yaml, load_txt, unspecified_argument
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event
from .bot import WiseBot

_DEFAULT_ROOT = str(Path(__file__).parents[0])


@fig.component('unwise-bot')
class UnwiseBot(WiseBot):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		del self.lines
		
		self._question_file = self._root / 'unwise_questions.txt'
		
	_initial_capital = 20.

	def _parse_number(self, money):
		try:
			money = float(money)
		except ValueError:
			money = float(money.replace(',', '.'))
		return money


	_game_title = 'Unwise Wagers!'
	async def _start_game(self, ctx, *args):
		# self._bids = {}
		await super()._start_game(ctx, *args)
		self.deltas = {}
		await self.table.send(f'Everyone starts with **${self._initial_capital:.2f}**.')


	async def _start_round(self):
		self._message_queries.clear()
		self._reaction_queries.clear()
		self._responses.clear()
		self._confirmed.clear()
		if not len(self._scores):
			self._scores = {player: self._initial_capital for player in self.players}

		self._round_count += 1
		await self.table.send(f'Round {self._round_count} begins! Submit your bids to become question master.')
		await self._collect_bids(self.players, self._resolve_master_bids, funds=self._scores, prompt='Submit a bid to be question master.')
	
	

	async def _submit_response(self, message, full_fmt='\n*{start} {response}*\n'):
		await super()._submit_response(message, full_fmt='\n*{start}*\n**{response}**\n')
	
	
	def _make_bid_request(self, bidders, callback, funds=None, bids=None):
		
		async def bid_request(message):
			nonlocal bids
			try:
				bid = self._parse_number(message.clean_content)
			except ValueError:
				await message.channel.send('Failed to parse your bid, try writing just the number '
				                           'without any extra spaces or punctuation.')
			else:
				
				if funds is not None and message.author in funds:
					fixed = max(0., min(funds[message.author], bid))
					
					if fixed != bid:
						await message.channel.send(f'Your bid exceeded your available funds, '
						                           f'so it was amended from ${bid:.2f} to ${fixed:.2f}')
						bid = fixed
				
				bids[message.author] = bid
				
				self._status = 'Waiting for {} to submit bids'.format(', '.join(p.display_name for p in bidders
				                                                                if p not in bids))
				
				await message.channel.send(f'You have submitted a bid of **${bid:.2f}**')
				
				if len(bids) == len(bidders):
					await callback(bids)
				
				return 'done'
		return bid_request
		
		
	async def _collect_bids(self, bidders, callback, funds=None, bids=None, prompt='Submit a bid'):
		if bids is None:
			bids = {}
		for player in bidders:
			# await self.interfaces[player].send(f'{player.mention}: Bid how much you would be willing to '
			#                                    f'pay to be question master.')
			await self._request_bid(player, self._make_bid_request(bidders, callback, funds=funds, bids=bids),
			                        prompt=prompt)
	
	
	async def _request_bid(self, player, callback, prompt='Submit a bid'):
		comm = self.interfaces[player]
		await comm.send(f'{player.mention}: {prompt}')
		await self.register_message_query(comm, player, callback)


	async def _resolve_master_bids(self, bids):
		self.deltas = {player: 0. for player in self.players}
		
		wts = {player: bid/self._scores[player] for player, bid in bids.items()}
		maxbid = max(wts.values())
		winners = [player for player, bid in wts.items() if bid == maxbid]
		winner = random.choice(winners)
		del wts[winner]
		cost = max(wts.values()) * self._scores[winner]
		await self.table.send(f'{winner.display_name} wins the bid, paying **${cost:.2f}**.')

		self.question_master = winner
		self.pot = cost
		self._scores[self.question_master] -= self.pot
		self.deltas[self.question_master] -= self.pot
		
		await self._collect_question()
		
		
	async def _collect_question(self):
		comm = self.interfaces[self.question_master]
		self._status = f'Waiting for the question master {self.question_master.display_name} to write a question.'
		await comm.send(f'{self.question_master.mention}: Choose a question and write here (without the answer)')
		await self.register_message_query(comm, self.question_master, self._ask_master)
		
		
	async def _ask_master(self, message):
		self.question = message.clean_content
		
		comm = self.interfaces[self.question_master]
		await comm.send(f'{self.question_master.mention}: Write the correct answer to the question '
		                f'(you will be asked to confirm afterwards)')
		await self.register_message_query(comm, self.question_master, self._ask_answer)
		
		return 'done'
		
	
	async def _ask_answer(self, message):
		self.answer = message.clean_content
		
		comm = self.interfaces[self.question_master]
		await comm.send(f'{message.author.mention} Confirm the question and answer:')
		await comm.send(f'Question: *{self.question}*')
		msg = await comm.send(f'Correct answer: **{self.answer}**')
		await self.register_reaction_query(msg, self._confirm_qa, self._accept_mark, self._reject_mark)
	

	async def _request_response(self, player, request='Compose an ending to the saying here'):
		return await super()._request_response(player, request='Answer the question')
	
	
	def _pick_query(self):
		pass
		# pick = random.randint(0, len(self.lines) - 1)
		# self._line = self.lines[pick]
		# del self.lines[pick]
	
	
	async def _confirm_qa(self, reaction, user):
		if reaction.emoji == self._accept_mark:
			await super()._start_round(False, required_responses=[p for p in self.players if p != self.question_master])
			# await self.interfaces[self.question_master].send('Your response has been recorded.')
		else:
			await self._collect_question()
		return 'done'
	
	
	def _prepare_options(self, options):
		
		if self._question_file is not None:
			with self._question_file.open('a') as f:
				f.write(f'{self.question}\n{repr(options)}\n{self.question_master.display_name}\n\n')
		
		try:
			options = [x[1] for x in sorted([(self._parse_number(o),o) for o in options])]
		except ValueError:
			self._rng.shuffle(options)
		return options
	
	
	def _gen_title(self):
		start = self.question
		if self.hint is None:
			init = f'Question: *{start}*'
		else:
			raise NotImplementedError
			origin = self.hint if self.hint == 'saying of India' else self.hint + ' saying'
			init = f' \nThere\'s an old **{origin}**: \n\n*{start}* ...\n '
		return init
	
	
	async def _count_points(self, fooled, correct, cycles):
		del fooled[self.question_master]
		
		# deltas = {player: 0. for player in self.players}
		# deltas[self.question_master] = -self.pot
		
		ratios = [self._bids[winner] for winner in correct]
		total = sum(ratios)
		ratios = [r/total for r in ratios]
		
		winnings = {c:r*self.pot for c, r in zip(correct, ratios)}
		
		commissions = {}
		treat = 0.
		
		for fooler, fools in fooled.items():
			earnings = sum(self._bids[fool] for fool in fools)
			# if self._confirmed[fooler] != self.answer:
			# 	pass
			treat += earnings/2
			if fooler not in commissions:
				commissions[fooler] = 0.
			commissions[fooler] += earnings/2

		await self.table.send(f'The correct answer was: **{self.answer}**')
		
		for player in self.players:
			if player != self.question_master:
				result = []
				if player in commissions:
					result.append(f'earns **${commissions[player]:.2f}** from other players')
				if player in winnings:
					result.append(f'wins **${winnings[player]:.2f}**')
				
				if len(result):
					result = ' and '.join(result)
					await self.table.send(f'{player.display_name} {result}.')
		
		await self.table.send(f'The question master {self.question_master.display_name} earns **${treat:.2f}** '
		                      f'for fooling other players')
		
		if not len(winnings):
			self._scores[self.question_master] += self.pot
			self.deltas[self.question_master] += self.pot
		
		for player in cycles:
			self._scores[self.question_master] += self._bids[player]
			self.deltas[self.question_master] += self._bids[player]
		for player, val in winnings.items():
			self._scores[player] += val + self._bids[player]
			self.deltas[player] += val + self._bids[player]
		for player, val in commissions.items():
			self._scores[player] += val
			self.deltas[player] += val
		self._scores[self.question_master] += treat
		self.deltas[self.question_master] += treat
		

	@as_command('cash')
	async def _check_cash(self, ctx):
		money = self._scores.get(ctx.author, None)
		if money is None:
			await ctx.send(f'No funds found.')
		else:
			await ctx.send(f'You have ${money:.2f}.')
	
	
	@as_command('challenge')
	async def _on_challenge(self, ctx, amount):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		
		amount = float(amount)
		
		punishment = ''
		if amount > 0:
			punishment = f'Additionally, **${amount}** will be deducted from the question master ' \
			             f'{self.question_master.display_name} and distributed to the other players for providing ' \
			             f'the wrong answer.'
			
		await self.table.send(f'The previous question has been challenged, so all wins and losses will be reverted. '
		                      f'{punishment}')
		
		for player, delta in self.deltas.items():
			self._scores[player] -= delta
		
		amount = min(amount, self._scores[self.question_master])
		
		self._scores[self.question_master] -= amount
		part = amount / (len(self.players) - 1)
		
		for player in self.players:
			if player != self.question_master:
				self._scores[player] += part
		
		await self.table.send('Carry on.')
		

	async def _present_options(self, fmt='{idx} ... *{ending}*'):
		return await super()._present_options(fmt= '{idx}  **{ending}**')
	
	
	async def _present_votes(self, inds, waiting_for=None):
		self._inds = inds
		await self._collect_bids([p for p in self.players if p != self.question_master], self._resolve_player_bids,
		                         funds=self._scores, prompt='Submit a bet')
	
	
	async def _resolve_player_bids(self, bids):
		self._bids = bids
		for player, bid in bids.items():
			await self.table.send(f'{player.display_name} bets ${bid:.2f}.')
			self._scores[player] -= bid
			self.deltas[player] -= bid
		await super()._present_votes(self._inds, waiting_for=[p for p in self.players if p != self.question_master],
		                             request='Select the correct answer to the question.')
	
	
	async def _end_round(self, score_fmt='**{}** point/s'):
		await super()._end_round(score_fmt='**${:.2f}**')

	
