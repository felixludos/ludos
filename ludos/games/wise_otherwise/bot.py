from pathlib import Path
import random
import discord

from omnibelt import load_yaml, load_txt, unspecified_argument
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event

# from tabulate import tabulate

_DEFAULT_ROOT = str(Path(__file__).parents[0])

@fig.Component('wise-bot')
class WiseBot(DiscordBot):
	def __init__(self, A, root=unspecified_argument, **kwargs):
		if root is unspecified_argument:
			root = A.pull('root', _DEFAULT_ROOT)
		super().__init__(A, **kwargs)
		self._root = Path(root) / 'data'
		# self._root = Path(root) / 'test-data'
		if root is not None:
			self.lines = self._load_data(self._root)
			# self.lines = self._load_data(Path(root) / 'test-data')
		# print(len(self.lines))
		
		
	def _load_data(self, root):
		root = Path(root)
		
		spath = root / 'starts.yaml'
		data = load_yaml(spath)
		raw = load_txt(spath).split('\n')
		nums = [int(r[2:]) for r in raw if len(r) and r[0] == '#']
		starts = {n: data[i * 5:(i + 1) * 5] for i, n in enumerate(nums)}
		
		epath = root / 'ends.yaml'
		ends = load_yaml(epath)
		
		for i, lines in starts.items():
			for line, end in zip(lines, ends[i]):
				line['end'] = end
		return [line for ind in sorted(list(starts.keys())) for line in starts[ind]]
	
	
	# @as_command('ping')
	# async def on_ping(self, ctx):
	# 	role = ' (admin)' if str(ctx.author) in self.admins else ''
	# 	await ctx.send(f'Hello, {ctx.author.display_name}{role}')
	
	
	def _gen_title(self):
		start = self.question
		if self.hint is None:
			init = f'*{start}*'
		else:
			origin = self.hint if self.hint == 'saying of India' else self.hint + ' saying'
			init = f' \nThere\'s an old **{origin}**: \n\n*{start}* ...\n '
		return init
	
	
	_game_title = 'Wise and Otherwise'
	async def _start_game(self, ctx, *args):
		self.question, self.answer, self.hint = None, None, None
		# self._line = None
		self._responses = {}
		self._confirmed = {}
		self._options = {}
		self._scores = {}
		self._round_count = 0
		self.votes = {}
		
		await self.table.send(f'Welcome to {self._game_title}!')
		await self._start_round()
		
		
	def _pick_query(self):
		pick = random.randint(0, len(self.lines) - 1)
		line = self.lines[pick]
		self.question = line['text']
		self.answer = line['end']
		self.hint = line['type']
		del self.lines[pick]
	
	
	async def _submit_response(self, message, full_fmt='\n*{start} {response}*\n'):
		response = message.clean_content
		self._responses[message.author] = message.clean_content
		comm = self.interfaces[message.author]
		await comm.send(f'{message.author.mention} Confirm your submission:')
		start = self.question
		msg = await comm.send(full_fmt.format(start=start, response=response))
		await self.register_reaction_query(msg, self._confirm_response, self._accept_mark, self._reject_mark)
		return 'done'

	
	async def _confirm_response(self, reaction, user):
		if reaction.emoji == self._accept_mark:
			self._confirmed[user] = self._responses[user]
			await self.interfaces[user].send('Your response has been recorded.')
		else:
			del self._responses[user]
			await self._request_response(user)
		
		self._status = 'Waiting for {} to submit responses'.format(', '.join(p.display_name for p in self._waiting_for
		                                                                     if p not in self._confirmed))
		
		if len(self._waiting_for) == len(self._confirmed):
			await self._present_options()
		return 'done'
	
	
	async def _request_response(self, player, request='Compose an ending to the saying here'):
		comm = self.interfaces[player]
		await comm.send(f'{player.mention}: {request}')
		await self.register_message_query(comm, player, self._submit_response)
		
		
	@as_command('skip')
	async def _skip_round(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		
		await self.table.send('**This round has been skipped**')
		
		for player in self.players:
			await self.interfaces[player].send('**This round has been skipped**')
		
		await self._start_round()
		
	
	async def _start_round(self, round_title=True, required_responses=None):
		if required_responses is None:
			required_responses = self.players
		self._pick_query()
		self._message_queries.clear()
		self._responses.clear()
		self._confirmed.clear()
		
		self._status = 'Waiting for {} to submit responses'.format(', '.join(p.display_name for p in required_responses))
		
		init = self._gen_title()
		
		if round_title:
			self._round_count += 1
			await self.table.send(f'Round {self._round_count} begins! Submit your responses.')
		
		self._waiting_for = required_responses
		
		for player in required_responses:
			await self.interfaces[player].send(init)
			await self._request_response(player)
	

	@as_event
	async def on_reaction_remove(self, reaction, user):
		if user in self.votes and reaction == self.votes[user]:
			del self.votes[user]

	
	def _prepare_options(self, options):
		self._rng.shuffle(options)
		return options
	
	
	async def _present_options(self, fmt='{idx} ... *{ending}*'):

		options = self._prepare_options([self.answer, *self._confirmed.values()])
		
		init = self._gen_title()
		
		self._options = {}
		inds = []
		await self.table.send(init)
		for idx, ending in zip(self._number_emojis[1:], options):
			inds.append(idx)
			self._options[idx] = ending
			await self.table.send(fmt.format(idx=idx, ending=ending))
		
		self.votes.clear()
		await self._present_votes(inds)
		
		
	async def _present_votes(self, inds, waiting_for=None, request='Select the correct ending of the saying.'):
		if waiting_for is None:
			waiting_for = self.players
		self._waiting_for = waiting_for
		
		for player in waiting_for:
			comm = self.interfaces[player]
			msg = await comm.send(f'{player.mention}: {request}')
			await self.register_reaction_query(msg, self._count_vote, *inds)
		
		self._status = 'Waiting for {} to vote for an ending.'.format(', '.join(p.display_name for p in self._waiting_for))
		
	
	async def _count_vote(self, reaction, user):
		if user in self.votes:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)
		self.votes[user] = reaction
		
		self._status = 'Waiting for {} to vote for an ending.'.format(', '.join(p.display_name for p in self._waiting_for
		                                                                        if p not in self.votes))

		if len(self.votes) == len(self._waiting_for):
			self._reaction_queries.clear()
			await self._resolve_round()
		
		
	async def _resolve_round(self):
		
		picks = {player: self._options[vote.emoji] for player, vote in self.votes.items()}
		
		fooled = {player: [] for player in self.players}
		correct = []
		cycles = set()
		
		for player, pick in picks.items():
			if pick == self.answer:
				correct.append(player)
			
			foolers = {author for author, response in self._confirmed.items() if response == pick}
			for author in foolers:
				if author != player:
					fooled[author].append(player)
				
			if len(foolers) == 1 and player in foolers:
				cycles.add(player)
		
		await self._count_points(fooled, correct, cycles)
		await self._end_round()
		
	
	async def _count_points(self, fooled, correct, cycles):
		
		points = {player: len(fools) + int(player in correct) for player, fools in fooled.items()}

		trust = {player: [fooler for fooler, fools in fooled.items() if player in fools]
		         for player in self.players}
		for player, picked in trust.items():
			
			result = ['the ending of ' + ', '.join(a.display_name for a in picked)] if len(picked) else []
			if player in correct:
				result.append('the __correct__ ending')

			result = ' and '.join(result)
			await self.table.send(f'{player.display_name} picked {result}.')
		
		correct = [emo for emo, text in self._options.items() if text == self.answer][0]
		await self.table.send(f'The correct ending is: {correct}')
		
		for player, score in points.items():
			if player in self._scores:
				self._scores[player] += score
			else:
				self._scores[player] = score
		
	
	async def _end_round(self, score_fmt='**{}** point/s'):
		
		await self.table.send(f'End of Round {self._round_count}.\n ')
		
		for player, score in sorted(self._scores.items(), key=lambda x: x[1], reverse=True):
			score = score_fmt.format(score)
			await self.table.send(f'{player.display_name} has {score}.')
		
		# await self.table.send(' ')
		
		await self._start_round()
		
		