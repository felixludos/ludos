from pathlib import Path
import random
import requests
import discord

from omnibelt import load_yaml, load_txt, unspecified_argument
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event

# from tabulate import tabulate

_DEFAULT_ROOT = Path(__file__).parents[0]

BASE_URL = "http://numbersapi.com/"
OPTIONS = ['trivia', 'math', 'date', 'year']


@fig.component('wits-bot')
class WitsBot(DiscordBot):
	
	_number_of_candidates = 7
	
	_prob_cats = {'trivia': 7, 'math': 0, 'year': 4}
	
	_starting_money = 0
	_author_reward = 3
	
	_cut_millions = True
	_display_estimate_authors = True
	_payouts = {
		1: [2],
		2: [3, 3],
		3: [3, 2, 3],
		4: [4, 3, 3, 4],
		5: [4, 3, 2, 3, 4],
		6: [5, 4, 3, 3, 4, 5],
		7: [5, 4, 3, 2, 3, 4, 5],
	}
	_all_too_high_payout = 6
	
	@staticmethod
	def get_number_fact(option='trivia', number='random'):
		if option not in OPTIONS:
			raise ValueError(f"Invalid option. Available options are: {', '.join(OPTIONS)}")
		
		url = f"{BASE_URL}{number}/{option}"
		response = requests.get(url)
		
		if response.status_code == 200:
			raw = response.text
			path = _DEFAULT_ROOT / 'data' / 'past_facts.txt'
			with open(path, 'a') as f:
				f.write(raw + '\n')
			return raw
		else:
			response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code

	@classmethod
	def request_question(cls, option='trivia', number='random'):
		fact = cls.get_number_fact(option, number)
		index = fact.find(' is ')
		assert index > 0, f"Invalid fact: {fact!r}"
		answer = fact[:index]
		question = f'What{fact[index:-1]}?'
		return {'cat': option, 'question': question, 'answer': answer}
	
	
	def generate_question(self):
		fuel = 10
		while fuel > 0:
			fuel -= 1
			try:
				pick = random.choices(list(self._prob_cats.keys()), list(self._prob_cats.values()))[0]
				info = self.request_question(pick)
				question = info['question']
				answer = int(info['answer'])
				
				if self._cut_millions and answer > 1e7:
					question = question.replace('What', 'What (in millions)') #+ ' (hint: >10 million)'
					answer = int(answer / 1e6)
				
				info['question'] = question
				info['answer'] = answer
				yield info
			except (requests.HTTPError, ValueError):
				pass
		raise ValueError('Could not generate enough questions')
	
	
	game_title = 'Wits and Wagers'
	async def _start_game(self, ctx, *args):
		self.estimates = {}
		self.options = []
		self.bets = {}
		self.bet_options = {}
		self.votes = {}
		self.money = {player: self._starting_money for player in self.players}
		
		self._all_too_high_payout -= max(0, 4 - len(self.players))
		
		total = sum(self._prob_cats.values())
		self._prob_cats = {k: v / total for k, v in self._prob_cats.items()}

		self.master = None
		self.round_count = 0
		self.player_order = self.players.copy()
		random.shuffle(self.player_order)
		
		self.candidates = {}
		self.question, self.answer, self.question_type = None, None, None
		
		await self.table.send(f'Welcome to {self.game_title}!')
		await self.start_round()
	
	
	@as_command('skip', brief='(admin) Skip current round')
	async def skip_round(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		
		await self.table.send('**This round has been skipped**')
		
		for player in self.players:
			await self.interfaces[player].send('**This round has been skipped**')
		
		await self.start_round()
	
	
	@as_command('money', brief='Show money of each player')
	async def on_money(self, ctx):
		lines = []
		for player in self.player_order:
			lines.append(f'{player.display_name} has {self.money[player]}')
		await ctx.send('\n'.join(lines))
	
	
	@as_command('transfer', brief='(admin) Transfer money to a player')
	async def on_transfer(self, ctx, player, delta):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		
		user = discord.utils.get(self.players, display_name=message.clean_content)
		num = int(delta)
		self.money[user] += num
		await ctx.send(f'{user.display_name} now has {self.money[user]}.')
	
	
	async def start_round(self, round_title=True):
		self.round_count += 1
		self.master = self.player_order[self.round_count % len(self.players)]
		
		await self.table.send(f'Round {self.round_count} begins! '
		                      f'{self.master.display_name} must select the next question.')
		
		candidates = [candidate for _, candidate in zip(range(self._number_of_candidates), self.generate_question())]
		assert len(self._number_emojis) > len(candidates), f'Not enough emojis for {len(candidates)} candidates'
		emojis = self._number_emojis[1:len(candidates) + 1]
		self.candidates = dict(zip(emojis, candidates))
		
		lines = [f'{self.master.mention} Select which question you would like everyone to answer and bet on:']
		for emoji in emojis:
			candidate = self.candidates[emoji]
			lines.append(f'{emoji} {candidate["question"]}')
		
		self._status = f'Waiting for {self.master.display_name} to select a question'
		
		prompt = '\n'.join(lines)
		msg = await self.interfaces[self.master].send(prompt)
		await self.register_reaction_query(msg, self.choose_candidate, *emojis)
		return 'done'
		
		
	async def choose_candidate(self, reaction, user):
		if user == self.master:
			pick = self.candidates.get(reaction.emoji, None)
			await self.prompt_for_estimates(pick)
			return 'done'
			

	async def prompt_for_estimates(self, pick):
		self.question = pick['question']
		self.answer = pick['answer']
		self.question_type = pick['cat']
		
		self.estimates.clear()
		await self.table.send(f'**{self.question}**')
		
		for player in self.players:
			comm = self.interfaces[player]
			await comm.send(f'**{self.question}**\n{player.mention} Provide your estimate (enter a whole number only).')
			await self.register_message_query(comm, player, self.submit_estimate)
		
		self.missing_responses = set(self.players)
		self._status = f'Waiting for estimates from {", ".join(p.display_name for p in self.missing_responses)}'
		
	
	async def submit_estimate(self, message):
		try:
			num = int(message.clean_content)
		except ValueError:
			await message.channel.send(f'Invalid estimate: {message.clean_content} '
			                           f'(write a whole number without any letters)')
			return
		
		self.estimates[message.author] = num
		await message.channel.send(f'Your estimate of **{num}** has been recorded.')
		
		self.missing_responses.discard(message.author)
		if len(self.missing_responses) == 0:
			await self.prompt_for_bets()
			return True
		
		self._status = f'Waiting for estimates from {", ".join(p.display_name for p in self.missing_responses)}'
	
		
	async def prompt_for_bets(self):
		self.votes.clear()
		self.bets.clear()
		self.bet_options.clear()
		self.collecting_bets = True
		
		self.authors = {}
		for author, estimate in self.estimates.items():
			self.authors.setdefault(estimate, []).append(author)
		for estimate, authors in self.authors.items():
			self.authors[estimate] = sorted(authors, key=lambda x: x.display_name)
		
		option_order = sorted(self.authors.items(), key=lambda x: (x[0], tuple((a.display_name for a in x[1]))))
		
		correct = self.answer
		best = None
		for estimate, authors in reversed(option_order):
			if estimate <= correct:
				best = estimate
				break
		
		option_order = [(estimate, authors, estimate == best) for estimate, authors in option_order]
		
		N = len(option_order)
		if N in self._payouts:
			payouts = self._payouts[N].copy()
		else:
			payouts = self._payouts[6 if N % 2 == 0 else 7].copy()
			payouts = [5]*((N-6)//2) + payouts + [5]*((N-6)//2)
		
		lines = [f'{self._number_emojis[0]} All too high. ({self._all_too_high_payout}:1)']
		for emoji, (estimate, authors, winner), payout in zip(self._number_emojis[1:], option_order, payouts):
			line = [emoji, f'**{estimate}**', f'({payout}:1)']
			if self._display_estimate_authors:
				line.append(f'*({", ".join(a.display_name for a in authors)})*')
			lines.append(' '.join(line))
			self.bet_options[emoji] = (winner, estimate, payout, authors)
		
		await self.table.send('\n'.join(lines))
		
		counts = [self._number_emojis[2], self._number_emojis[3], self._number_emojis[4],
		          self._number_emojis[5], self._number_emojis[10]]
		
		bet_msg = await self.table.send(f'{self.guild.default_role} Place extra your bets (1 free if none selected)')
		await self.register_reaction_query(bet_msg, self.submit_bets, *counts, remove_callback=self.remove_bet)
		
		msg = await self.table.send(f'{self.guild.default_role} Select the best estimate to bet on')
		# msg = await self.table.send(f'Select the best estimate to bet on')
		await self.register_reaction_query(msg, self.submit_choice, *self._number_emojis[:len(lines)])
		
		self.missing_responses = set(self.players)
		self._status = f'Waiting for bets from {", ".join(p.display_name for p in self.missing_responses)}'
		
	
	async def submit_bets(self, reaction, user):
		if not self.collecting_bets:
			return True
		if reaction.emoji in self._number_emojis:
			index = self._number_emojis.index(reaction.emoji)
			if user not in self.bets:
				self.bets[user] = 0
			self.bets[user] += index
	
	async def remove_bet(self, reaction, user):
		if not self.collecting_bets:
			return True
		if reaction.emoji in self._number_emojis:
			index = self._number_emojis.index(reaction.emoji)
			if user in self.bets:
				self.bets[user] = max(1, self.bets[user]-index)
	
	async def submit_choice(self, reaction, user):
		if user in self.votes and reaction.emoji in self.bet_options:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)
		self.votes[user] = reaction
		
		self.missing_responses.discard(user)
		if len(self.missing_responses) == 0:
			await self.resolve_bets()
			return True
		
		self._status = f'Waiting for bets from {", ".join(p.display_name for p in self.missing_responses)}'
		
	async def remove_choice(self, reaction, user):
		if user in self.votes and self.votes[user].emoji == reaction.emoji:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)

	async def resolve_bets(self):
		self.collecting_bets = False
		
		lines = [f'The correct answer is **{self.answer}**.\n']
		
		winning_emoji = [emoji for emoji, (winner, estimate, payout, authors) in self.bet_options.items() if winner][0]
		payout = self.bet_options[winning_emoji][2]
		winning_authors = self.bet_options[winning_emoji][3]
		
		players = [player for player in sorted(self.players, key=lambda p: p.display_name)]
		winners = [player for player, rct in self.votes.items() if rct.emoji == winning_emoji]
		
		results = {}
		
		for player in players:
			bet = max(1, min(self.money[player], self.bets.get(player, 1)))
			risk = max(bet - 1, 0)
			
			terms = [f'{player.display_name} bet {bet}']
			
			results[player] = 0
			
			if self.votes[player].emoji == winning_emoji:
				terms.append(f'and won **{bet * payout}**')
				results[player] += bet * payout
			elif risk > 0:
				terms.append(f'and lost **{risk}**')
				results[player] -= change
			
			if player in winning_authors:
				results[player] += self._author_reward
				terms.append(f'(gaining **{self._author_reward}** bonus)')

			self.money[player] = max(results[player]+self.money[player], 0)
			
			lines.append(' '.join(terms))
			
		lines.append('\n__Current Score__')
		
		for player in sorted(players, key=lambda p: self.money[p], reverse=True):
			lines.append(f'{player.display_name}: **{self.money[player]}**')
		
		lines.append('------------------')
		await self.table.send('\n'.join(lines))
		
		await self.start_round()

