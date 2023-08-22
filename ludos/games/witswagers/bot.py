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


@fig.component('wise-bot')
class WitsBot(DiscordBot):
	
	_number_of_candidates = 7
	
	_prob_cats = {'trivia': 0.6, 'math': 0.1, 'year': 0.3}
	
	_starting_money = 50
	
	_display_estimate_authors = False
	
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
		question = f'What{fact[index:]}?'
		return {'cat': option, 'question': question, 'answer': answer}
	
	
	def generate_question(self):
		fuel = 10
		while fuel > 0:
			fuel -= 1
			try:
				pick = random.choices(list(self._prob_cats.keys()), list(self._prob_cats.values()))[0]
				yield self.request_question(pick)
			except requests.HTTPError:
				pass
		raise ValueError('Could not generate enough questions')
	
	
	_game_title = 'Wits and Wagers'
	async def _start_game(self, ctx, *args):
		self.estimates = {}
		self.options = []
		self.bet_options = {}
		self.bets = {}
		self.votes = {}
		
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
		
		lines = [f'{self.master.mention} Select which fact you would like everyone to bet on:']
		for emoji in emojis:
			candidate = self.candidates[emoji]
			lines.append(f'{emoji} {candidate["question"]}')
		
		self._status = f'Waiting for {self.master.display_name} to select a fact'
		
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
			await message.channel.send(f'Invalid estimate: {message.clean_content}')
			return
		
		self.estimates[message.author] = num
		await message.channel.send(f'Your estimate of **{num}** has been recorded.')
		
		self.missing_responses.discard(message.author)
		if len(self.missing_responses) == 0:
			await self.prompt_for_bets()
			return True
		
		self._status = f'Waiting for estimates from {", ".join(p.display_name for p in self.missing_responses)}'
	
		
	_payouts = [5, 4, 3, 2, 3, 4, 5]
		
	_all_too_high = '**All too high.**' # payout 6:1
	async def prompt_for_bets(self):
		self.bets.clear()
		self.bet_options.clear()
		
		option_order = sorted(self.estimates.items(), key=lambda x: (x[1], x[0].display_name))
		
		lines = []
		for emoji, (user, value) in zip(self._number_emojis,
		                                [(None, self._all_too_high), *option_order]):
			if user is None:
				lines.append(f'{emoji} {value}')
			else:
				lines.append(f'{emoji} **{value}** ({user.display_name})'
				             if self._display_estimate_authors else f'{emoji} **{value}**')
			self.bet_options[emoji] = value
			
		await self.table.send('\n'.join(lines))
		
		for player in self.players:
			comm = self.interfaces[player]
			await comm.send(f'**{self.question}**\n{player.mention} Place your bets (enter a whole number only).')
			await self.register_message_query(comm, player, self.submit_bets)
		
		self._status = f'Waiting for bets from {", ".join(p.display_name for p in self.missing_responses)}'
		
	
	async def submit_bets(self, message):
		pass



