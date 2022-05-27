import random
import discord

from omnibelt import get_printer, unspecified_argument
import omnifig as fig

from ..interface import Interface
from .compat import OmniBot, as_command, as_event

prt = get_printer(__file__)


class AdminError(Exception):
	def __init__(self, name):
		super().__init__(f'{name} doesn')



@fig.Component('discord-bot')
class DiscordBot(Interface, OmniBot, name='discord'):
	def __init__(self, A, admins=None, intents=unspecified_argument, seed=unspecified_argument, **kwargs):
		
		if intents is unspecified_argument:
			intents = discord.Intents.default()
			intents.members = True
			
		if admins is None:
			admins = A.pull('admins', [])
		
		if seed is unspecified_argument:
			seed = A.pull('seed', None)
		
		super().__init__(A, intents=intents, **kwargs)
		self.register_buffer('admins', set(admins))
		
		self._rng = random.Random()
		if seed is not None:
			self._rng.seed(seed)
		
		self.interfaces = {}
		self._roles = {}
		self._message_queries = {}
		self._reaction_queries = {}
		self._reaction_remove_queries = {}
	
	
	async def register_message_query(self, channel, user, callback):
		self._message_queries[channel, user] = callback
	
	async def register_reaction_query(self, message, callback, *options, remove_callback=None):
		for option in options:
			await message.add_reaction(option)
		self._reaction_queries[message] = callback
		if remove_callback is not None:
			self._reaction_remove_queries[message] = remove_callback
	
	@as_event
	async def on_message(self, message):
		if message.author == self.user:
			return
		
		key = (message.channel, message.author)
		if not message.clean_content.startswith('.') and key in self._message_queries \
				and self._message_queries[key] is not None:
			callback = self._message_queries[key]
			self._message_queries[key] = None
			out = await callback(message)
			if out is None:
				self._message_queries[key] = callback
			elif key in self._message_queries and self._message_queries[key] is None:
				del self._message_queries[key]
		
		await self.process_commands(message)
	
	
	@as_event
	async def on_reaction_remove(self, reaction, user):
		if user == self.user:
			return
		
		key = reaction.message
		if key not in self._reaction_queries and key in self._reaction_remove_queries:
			del self._reaction_remove_queries[key]
		if key in self._reaction_remove_queries and self._reaction_remove_queries[key] is not None:
			callback = self._reaction_remove_queries[key]
			self._reaction_remove_queries[key] = None
			out = await callback(reaction, user)
			if out is None:
				self._reaction_remove_queries[key] = callback
			elif key in self._reaction_queries and self._reaction_remove_queries[key] is None:
				del self._reaction_remove_queries[key]
		if key not in self._reaction_queries:
			del self._reaction_remove_queries[key]
	

	@as_event
	async def on_reaction_add(self, reaction, user):
		if user == self.user:
			return
		
		key = reaction.message
		if key in self._reaction_queries and self._reaction_queries[key] is not None:
			callback = self._reaction_queries[key]
			self._reaction_queries[key] = None
			out = await callback(reaction, user)
			if out is None:
				self._reaction_queries[key] = callback
			elif key in self._reaction_queries and self._reaction_queries[key] is None:
				del self._reaction_queries[key]
	
	
	def _insufficient_permissions(self, user):
		return str(user) not in self.admins
	
	
	@as_command('ping')
	async def on_ping(self, ctx):
		role = ' (admin)' if str(ctx.author) in self.admins else ''
		await ctx.send(f'Hello, {ctx.author.display_name}{role}')
	
	
	async def _create_channel(self, name, *members, reason=None, category=None,
	                          overwrites=None, private=False, remove_existing=False):
		if overwrites is None:
			overwrites = {self.guild.default_role: discord.PermissionOverwrite(view_channel=False)}
			# admin_role = get(guild.roles, name="Admin")
			# overwrites = {
			# 	guild.default_role: discord.PermissionOverwrite(read_messages=False),
			# 	member: discord.PermissionOverwrite(read_messages=True),
			# 	admin_role: discord.PermissionOverwrite(read_messages=True)
			# }
			
		if not private:
			overwrites[discord.utils.get(self.guild.roles, name='Player')] = discord.PermissionOverwrite(view_channel=True)
			overwrites[discord.utils.get(self.guild.roles, name='Spectator')] = discord.PermissionOverwrite(send_messages=True,
				view_channel=True)
		
		if name is None:
			assert False
			
		_matches = [c for c in self.guild.channels if c.name == name]
		if len(_matches):
			return _matches[0]
		
		if category is None:
			category = self.gameroom
			
		members = set(members)
		for member in self.players:
			if member in members:
				overwrites[member] = discord.PermissionOverwrite(send_messages=True, view_channel=True)
			else:
				overwrites[member] = discord.PermissionOverwrite(send_messages=False, view_channel=not private)
		
		channel = await self.guild.create_text_channel(name, reason=reason, category=category,
		                                               overwrites=overwrites)
		# if remove_existing:
		# 	await channel.purge(limit=100)
		return channel
		
	
	async def _setup_player(self, member):
		name = str(member.display_name)
		channel = await self._create_channel(f'{name}-interface', member, private=True, remove_existing=True)
		await channel.send('Use this channel to talk to the game bot (in secret)')
		print(f'{name} is setup')
		self.interfaces[member] = channel
		return member


	async def on_ready(self):
		print(f'Logged on as {self.user}')
		
		self._status = 'No game running.'
		
		# self.guild = self.guilds[0]
		self.guild = discord.utils.get(self.guilds, name='games')
		# self.gameroom = [c for c in self.guild.channels if c.name == 'GameRoom'][0]
		
		# guild = self.guilds[0]
		# await guild.create_role(name='admin')
		
		
		# msg = await self.table.send(f'Ready')
		# await msg.add_reaction(self._accept_mark)
		# await msg.add_reaction(self._reject_mark)

	
	@as_command('start')
	async def on_start(self, ctx, *args):
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

		self._status = ''
		await self._start_game(ctx, *args)
	
	
	@as_command('status')
	async def on_status(self, ctx):
		await ctx.send(self._status)
	
	
	async def _start_game(self, ctx, *args):
		raise NotImplementedError

	
	@as_command('checkpoint')
	async def on_checkpoint(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		self.checkpoint()
		await ctx.send(f'Bot state has been saved.')
	
	
	_game_list = {
		'🖌': 'Dixit (3+) (Discord)',
		'🔮': 'Mysterium (3+) (Discord)',
		'🗡️': 'Murder (6-10) (Discord)',
		'🧐': 'Unwise Wagers (3+) (Discord)',
		'👑': 'Aristocracy (2-5) (Telecave)',
		'🗯️': 'Bluff! (2+) (Telecave)',
		'👀': 'Spot It! (2+) (Telecave)',
		'💀': 'Skull (3-6) (BGA)',
		'🎭': 'Coup (2-8) (BGA)',
		# '💞': 'Love Letter (3-8)',
		'🧙': 'Wizard (3-6) (BGA)',
		# '📰': 'Letter Tycoon (2-5) (BGA)',
		# '🤠': 'Colt Express (2-6)',
		# '🐺': 'Werewolf (8-12)',
		# '🔫': 'Bang! (2-7)',
		# '🕌': 'Alhambra (2-6)',
		# '👁‍🗨': 'Mystic Dialogue (2+) (Discord)',
		# '🏠': 'Catan (3-4) (settler.io)',
		'⚗️': 'Innovation (2-4) (BGA)',
		# '🖋️': 'Wise and Otherwise (3+)',
		'🙃': 'Other',
	}
	
	@as_command('games')
	async def _on_game_vote(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		emojis = []
		lines = []
		for emoji, name in self._game_list.items():
			emojis.append(emoji)
			lines.append(f'{emoji} {name}')
			# await ctx.send(f'{emoji} {name}')
		
		lines.append('Vote for the games you want to play next')
		msg = await ctx.send('\n'.join(lines))
		for emoji in emojis:
			await msg.add_reaction(emoji)
	
	
	@as_command('shuffle')
	async def _on_shuffle(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		players = list(discord.utils.get(self.guild.roles, name='Player').members)
		random.shuffle(players)
		await ctx.send('{}'.format(', '.join(p.display_name for p in players)))
	
	
	_accept_mark = '✅'  # '✔️'
	_reject_mark = '❎'  # '❌'

	_vote_yes = '👍'
	_vote_no = '👎'
	
	_number_emojis = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '⏹', '⏺', '▶️', '⏫', '⏸']

# todo:
# - skip option in wise and otherwise
# - custom sayings in wise and otherwise


