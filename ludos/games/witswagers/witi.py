from pathlib import Path
import random, math
import requests
import discord

from omnibelt import load_yaml, load_txt, unspecified_argument
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event

# from tabulate import tabulate

_DEFAULT_ROOT = Path(__file__).parents[0]

BASE_URL = "http://numbersapi.com/"
OPTIONS = ['trivia', 'math', 'date', 'year']


def human_readable_number(num, significant_figures=1, units=None):
	# Default units if not provided
	if units is None:
		units = {
			"T": 1_000_000_000_000,
			"B": 1_000_000_000,
			"M": 1_000_000,
			"K": 1_000,
			"": 1
		}
	
	# Helper function to format number with significant figures
	def format_sig_figs(n, sig_figs):
		format_str = "{:." + str(sig_figs) + "g}"
		val = format_str.format(n)
		# remove trailing 0s
		if '.' in val:
			val = val.rstrip("0")
		# remove trailing .
		val = val.rstrip(".")
		return val
	
	# Sort units from largest to smallest
	sorted_units = sorted(units.items(), key=lambda x: x[1], reverse=True)
	
	for unit, threshold in sorted_units:
		if abs(num) >= threshold:
			return format_sig_figs(num / threshold, significant_figures) + unit
	
	return format_sig_figs(num, significant_figures)


@fig.component('witi-bot')
class WitiBot(DiscordBot):

	_number_of_candidates = 10
	
	_prob_cats = {'trivia': 7, 'math': 0, 'year': 3}
	
	_starting_money = 20
	_author_reward = 3
	_num_free_bets = 2

	_round_to_sigfigs = 4
	_units = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12, 'Q': 1e15}
	
	_display_estimate_authors = True
	_payouts = {
		1: [2],
		2: [3, 3],
		3: [3, 2, 3],
		4: [4, 3, 3, 4],
		5: [4, 3, 2, 3, 4],
		6: [5, 4, 3, 3, 4, 5],
		7: [5, 4, 3, 2, 3, 4, 5],
		8: [6, 5, 4, 3, 3, 4, 5, 6],
		9: [6, 5, 4, 3, 2, 3, 4, 5, 6],
	}
	_all_too_high_payout = 6

	
	def as_number(self, value):
		return int(value * (10 ** self._round_to_digits))
	
	def parse_number(self, raw: str):
		raw = raw.replace('$','').strip().lower()
		for unit, value in self._units.items():
			if raw.endswith(unit.lower()):
				raw = raw[:-len(unit)].strip()
				return float(raw) * value
		return float(raw)
	
	def present_number(self, num):
		if isinstance(num, int):
			return str(num)
		return human_readable_number(num, significant_figures=self.sigfigs, units=self._units)
	
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
		fuel = self._number_of_candidates * 3
		while fuel > 0:
			fuel -= 1
			try:
				pick = random.choices(list(self._prob_cats.keys()), list(self._prob_cats.values()))[0]
				info = self.request_question(pick)
				question = info['question']
				answer = int(info['answer'])
				
				if info['cat'] == 'year':
					info['sigfigs'] = len(str(answer))
				else:
					info['sigfigs'] = self._round_to_sigfigs
				
				# if self._cut_millions and answer > 1e7:
				# 	question = question.replace('What', 'What (in millions)') #+ ' (hint: >10 million)'
				# 	answer = int(answer / 1e6)
				
				info['question'] = question
				info['answer'] = answer
				yield info
			except (requests.HTTPError, ValueError):
				pass
		raise ValueError('Could not generate enough questions')
	
	
	game_title = 'Witty Wagers'
	async def _start_game(self, ctx, *args):
		self.estimates = {}
		self.options = []
		self.bets = {}
		self.ready = set()
		self.bet_options = {}
		self.votes = {}
		self.ranges = {}
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
		if self._starting_money > 0:
			await self.table.send(f'Each player starts with {self._starting_money} for betting.')
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
		
		user = discord.utils.get(self.players, display_name=player)
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
		self.sigfigs = pick['sigfigs']
		self.cat = pick['cat']
		
		if self.cat != 'year':
			self.answer = float(self.answer)
		
		self.estimates.clear()
		
		for player in self.players:
			comm = self.interfaces[player]
			await comm.send(f'**{self.question}**\n{player.mention} Provide your estimate (enter a number only).')
			await self.register_message_query(comm, player, self.submit_estimate)
		
		self.missing_responses = set(self.players)
		self._status = f'Waiting for estimates from {", ".join(p.display_name for p in self.missing_responses)}'
		
	
	async def submit_estimate(self, message):
		try:
			num = self.parse_number(message.clean_content)
		except ValueError:
			await message.channel.send(f'Invalid estimate: {message.clean_content} '
									   f'(write a number without any letters)')
			return
		
		if self.cat == 'year':
			num = int(num)
		
		self.estimates[message.author] = num
		await message.channel.send(f'Your estimate of **{self.present_number(num)}** has been recorded.')
		
		self.missing_responses.discard(message.author)
		if len(self.missing_responses) == 0:
			await self.prompt_for_bets()
			return True
		
		self._status = f'Waiting for estimates from {", ".join(p.display_name for p in self.missing_responses)}'
	
		
	async def prompt_for_bets(self):
		self.votes.clear()
		self.bets.clear()
		self.ready.clear()
		self.bet_options.clear()
		self.collecting_bets = True
		
		self.authors = {}
		for author, estimate in self.estimates.items():
			self.authors.setdefault(self.present_number(estimate), []).append(author)
		for estimate, authors in self.authors.items():
			self.authors[estimate] = sorted(authors, key=lambda x: x.display_name)

		option_order = sorted(self.authors.items(), key=lambda x: (self.parse_number(x[0]),
		                                                           tuple((a.display_name for a in x[1]))))

		await self.table.send(f'**{self.question}**')

		if len(option_order) == 1:
			pres, authors = option_order[0]
			pres_answer = self.present_number(self.answer)
			est = self.parse_number(pres)
			await self.table.send(f'All players guessed **{pres}**.')

			bet_emojis = '🔴', '🟢', '🔵'
			low, exact, high = self._payouts[3].copy()
			lines = [
				f'{bet_emojis[0]} Less than **{pres}** ({low}:1)',
				f'{bet_emojis[1]} Exactly **{pres}** ({exact}:1)',
				f'{bet_emojis[2]} More than **{pres}** ({high}:1)',
			]

			bet_options = {
				bet_emojis[0]: (self.answer < est, est, low, []),
				bet_emojis[1]: (pres_answer == pres, est, exact, authors),
				bet_emojis[2]: (self.answer > est, est, high, []),
			}

		else:
			bet_emojis = self._shape_emojis

			ests = [self.parse_number(estimate) for estimate, authors in option_order]
			bs = [a / 2 + b / 2 for a, b in zip(ests[:-1], ests[1:])]
			gold = int(sum(self.answer >= b for b in bs))
			assert 0 <= gold < len(ests), f'Invalid gold: {gold} for {len(ests)} estimates'

			if self.cat == 'year':
				# round bounds
				bs = [int(b) for b in bs]

			bounds = [self.present_number(b) for b in bs]
			# self.bounds = bounds
			ranges = [f'Less than **{bounds[0]}**',
					  *[f'More than **{a}** and up to **{b}**' for a, b in zip(bounds[:-1], bounds[1:])],
					  f'More than **{bounds[-1]}**']

			payouts = self._payouts[len(ranges)].copy()

			bet_options = {}
			lines = []
			for i, (emoji, rg, (middle, authors), payout) \
					in enumerate(zip(bet_emojis, ranges, option_order, payouts)):
				line = [emoji, rg, f'({payout}:1)']
				if self._display_estimate_authors:
					line.append(f'*({", ".join(a.display_name for a in authors)})*')
				lines.append(' '.join(line))
				bet_options[emoji] = (i == gold, middle, payout, authors)

		self.bet_options = bet_options
		self.free_bets = min(self._num_free_bets, len(bet_options) - 1)

		await self.table.send('\n'.join(lines))
		
		counts = [self._number_emojis[2], self._number_emojis[3],
				  self._number_emojis[4], self._number_emojis[5],
				  self._number_emojis[10]]
		
		bet_msg = await self.table.send(f'{self.guild.default_role} Place your extra bets '
										f'(sum of all selected are added to each of your bets)')
		await self.register_reaction_query(bet_msg, self.submit_bets, *counts, remove_callback=self.remove_bet)
		
		msg = await self.table.send(f'{self.guild.default_role} Select up to {self.free_bets} '
									f'estimate{"s" if self.free_bets > 1 else ""} to bet on')
		await self.register_reaction_query(msg, self.submit_choice, *self.bet_options.keys())

		msg = await self.table.send(f'{self.guild.default_role} Click here when you are ready for scoring.')
		await self.register_reaction_query(msg, self.submit_continue, self._accept_mark,
										   remove_callback=self.remove_ready)
		
		self.missing_responses = set(self.players)
		self._status = f'Waiting for {", ".join(p.display_name for p in self.missing_responses)}'

	async def submit_continue(self, reaction, user):
		if not self.collecting_bets:
			return True
		if reaction.emoji == self._accept_mark:
			self.missing_responses.discard(user)
		if len(self.missing_responses) == 0:
			await self.resolve_bets()
			return True
		self._status = f'Waiting for {", ".join(p.display_name for p in self.missing_responses)}'

	async def remove_ready(self, reaction, user):
		if not self.collecting_bets:
			return True
		if reaction.emoji == self._accept_mark:
			self.missing_responses.add(user)

		self._status = f'Waiting for {", ".join(p.display_name for p in self.missing_responses)}'
	
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
				self.bets[user] = max(0, self.bets[user]-index)
	
	async def submit_choice(self, reaction, user):
		if user in self.players and reaction.emoji in self.bet_options:
			self.votes.setdefault(user, []).append(reaction)

			if len(self.votes[user]) > self.free_bets:
				old = self.votes[user].pop(0)
				await old.remove(user)

	async def remove_choice(self, reaction, user):
		if user in self.votes and any(r.emoji == reaction.emoji for r in self.votes[user]):
			for i, r in enumerate(self.votes[user]):
				if r.emoji == reaction.emoji:
					del self.votes[user][i]
					break

	async def resolve_bets(self):
		self.collecting_bets = False

		winning_emoji = [emoji for emoji, (winner, estimate, payout, authors) in self.bet_options.items() if winner]
		# if len(winning_emoji) == 0:
		# 	winning_emoji = self._number_emojis[0]
		# 	self.bet_options[self._number_emojis[0]] = (True, None, self._all_too_high_payout, [])
		# else:
		# 	winning_emoji = winning_emoji[0]

		assert len(winning_emoji) == 1, f'Invalid winning emoji: {winning_emoji}'
		winning_emoji = winning_emoji[0]
		payout = self.bet_options[winning_emoji][2]
		winning_authors = self.bet_options[winning_emoji][3]
		
		players = [player for player in sorted(self.players, key=lambda p: (self.money[p], p.display_name))]
		winners = [player for player in players for rct in self.votes.get(player,[]) if rct.emoji == winning_emoji]
		
		lines = []
		
		if len(winners):
			lines.append(f'{", ".join(w.display_name for w in winners)} guessed correctly!\n')
		else:
			lines.append(f'No one guessed correctly!\n')
		
		lines.append(f'The correct answer is **{self.present_number(self.answer)}**.\n')
		
		results = {}
		
		for player in players:
			if not len(self.votes.get(player, [])):
				lines.append(f'{player.display_name} did not bet on any estimate.')
			else:
				picks = self.votes[player]
				bet = max(0, min(self.bets.get(player, 0), self.money[player]//len(picks)))
				risk = bet * len(picks)
				assert risk < self.money[player], f'Invalid bet: {bet} * {len(picks)} = {risk} >= {self.money[player]}'

				terms = [f'{player.display_name} bet', f'{bet} on' if bet > 0 else 'on',
						 f'{len(picks)} estimate{"s" if len(picks) > 1 else ""}']

				results[player] = 0

				bet = max(bet, 1) # "free" token

				if player in winners:
					winnings = max(bet, 1) * payout
					loss = risk - bet
				else:
					winnings = 0
					loss = risk
				bonus = self._author_reward if player in winning_authors else 0

				delta = winnings - loss + bonus
				results[player] = delta

				if winnings > 0:
					terms.append(f'gaining {winnings}')
				if loss > 0:
					if winnings > 0:
						terms.append('and')
					terms.append(f'losing {loss}')
				if bonus > 0:
					terms.append(f'(+{bonus} bonus)')

				terms.append(f' ->  **{delta}**')

				self.money[player] = max(results[player] + self.money[player], 0)

				lines.append(' '.join(terms))
			
		lines.append('\n__Current Score__')

		for player in sorted(players, key=lambda p: self.money[p], reverse=True):
			lines.append(f'{player.display_name}: **{self.money[player]}**')
		
		lines.append('------------------')
		await self.table.send('\n'.join(lines))
		
		await self.start_round()

