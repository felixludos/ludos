from pathlib import Path
import random
import discord

from omnibelt import load_yaml, load_txt
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event

_DEFAULT_ROOT = str(Path(__file__).parents[0])

@fig.Component('wise-bot')
class WiseBot(DiscordBot):
	def __init__(self, A, root=None, **kwargs):
		if root is None:
			root = A.pull('root', _DEFAULT_ROOT)
		super().__init__(A, **kwargs)
		self.lines = self._load_data(Path(root) / 'data')
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
	
	
	@as_command('status')
	async def on_status(self, ctx):
		await ctx.send(self._status)
	
	
	def _gen_title(self, line):
		start = line['text']
		origin = line['type'] if line['type'] == 'saying of India' else line['type'] + ' saying'
		init = f' \nThere\'s an old **{origin}**: \n\n*{start}* ...\n '
		return init
	
	
	@as_command('start')
	async def on_start(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
	
		gameroom = discord.utils.get(self.guild.channels, name='GameRoom')
		if gameroom is not None:
			for channel in gameroom.channels:
				await channel.delete()
			await gameroom.delete()
		self.gameroom = await self.guild.create_category_channel('GameRoom')
		
		# _players = ['bobmax', 'felixludos', 'Lauren', 'GooseOnTheLoose']
		player_role = discord.utils.get(self.guild.roles, name='Player')
		# _players = []
		# _members = {member.display_name: member for member in self.get_all_members()}
		# self._players = [_members[player] for player in _players]
		self.players = [player for player in player_role.members if not player.bot]
		for player in self.players:
			await self._setup_player(player)
		self.table = await self._create_channel('table', *self.players, remove_existing=True)
		
		self._line = None
		self._responses = {}
		self._confirmed = {}
		self._options = {}
		self._scores = {}
		self._round_count = 0
		self.votes = {}
		
		await self.table.send('Welcome to Wise and Otherwise!')
		await self._start_round()
		
		
	def _pick_query(self):
		pick = random.randint(0, len(self.lines) - 1)
		self._line = self.lines[pick]
		del self.lines[pick]
	
	
	_accept_mark = '✅'  # '✔️'
	_reject_mark = '❎'  # '❌'

	_number_emojis = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
	
	
	async def _submit_response(self, message):
		response = message.clean_content
		self._responses[message.author] = message.clean_content
		comm = self.interfaces[message.author]
		await comm.send(f'{message.author.mention} Confirm your submission:')
		start = self._line['text']
		msg = await comm.send(f'\n*{start} {response}*\n')
		await self.register_reaction_query(msg, self._confirm_response, self._accept_mark, self._reject_mark)
		return 'done'

	
	async def _confirm_response(self, reaction, user):
		if reaction.emoji == self._accept_mark:
			self._confirmed[user] = self._responses[user]
			await self.interfaces[user].send('Your response has been recorded.')
		else:
			del self._responses[user]
			await self._request_response(user)
		
		self._status = 'Waiting for {} to submit responses'.format(', '.join(p.display_name for p in self.players
		                                                                     if p not in self._confirmed))
		
		if len(self.players) == len(self._confirmed):
			await self._present_options()
		return 'done'
	
	
	async def _request_response(self, player):
		comm = self.interfaces[player]
		await comm.send(f'{player.mention}: Compose an ending to the saying here')
		await self.register_message_query(comm, player, self._submit_response)
		
	
	async def _start_round(self):
		self._pick_query()
		self._responses.clear()
		self._confirmed.clear()
		
		self._status = 'Waiting for {} to submit responses'.format(', '.join(p.display_name for p in self.players))
		
		init = self._gen_title(self._line)
		
		self._round_count += 1
		await self.table.send(f'Round {self._round_count} begins! Submit your responses.')
		for player in self.players:
			await self.interfaces[player].send(init)
			await self._request_response(player)
	

	@as_event
	async def on_reaction_remove(self, reaction, user):
		if user in self.votes and reaction == self.votes[user]:
			del self.votes[user]

	
	async def _present_options(self):
		
		options = [self._line['end'], *self._confirmed.values()]
		self._rng.shuffle(options)
		
		init = self._gen_title(self._line)
		
		self._options = {}
		inds = []
		await self.table.send(init)
		for idx, ending in zip(self._number_emojis[1:], options):
			inds.append(idx)
			self._options[idx] = ending
			await self.table.send(f'{idx} ... *{ending}*')
		
		self.votes.clear()
		
		for player, comm in self.interfaces.items():
			msg = await comm.send(f'{player.mention}: Select the correct ending of the saying.')
			await self.register_reaction_query(msg, self._count_vote, *inds)
		
		self._status = 'Waiting for {} to vote for an ending.'.format(', '.join(p.display_name for p in self.players))
		
	
	async def _count_vote(self, reaction, user):
		if user in self.votes:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)
		self.votes[user] = reaction
		
		self._status = 'Waiting for {} to vote for an ending.'.format(', '.join(p.display_name for p in self.players
		                                                                        if p not in self.votes))

		if len(self.votes) == len(self.players):
			self._reaction_queries.clear()
			await self._resolve_round()
		
		
	async def _resolve_round(self):
		
		picks = {player: self._options[vote.emoji] for player, vote in self.votes.items()}
		
		points = {player: 0 for player in self.players}
		
		for player, pick in picks.items():
		
			result = []
			
			for author in [author for author, response in self._confirmed.items() if response == pick]:
				if author != player:
					points[author] += 1
					result.append(author)
			
			if len(result):
				result = ['the ending of ' + ', '.join(a.display_name for a in result)]
		
			if pick == self._line['end']:
				points[player] += 1
				result.append('the correct ending')
			
			result = ' and '.join(result)
			await self.table.send(f'{player.display_name} picked {result}.')
		
		for player, score in points.items():
			if player in self._scores:
				self._scores[player] += score
			else:
				self._scores[player] = score
		
		await self.table.send(f'End of Round {self._round_count}.\n ')
		
		for player, score in self._scores.items():
			await self.table.send(f'{player.display_name} has **{score}** point/s.')
		
		await self.table.send(' ')
		
		await self._start_round()
		