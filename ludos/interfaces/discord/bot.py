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
	
	
	async def register_message_query(self, channel, user, callback):
		self._message_queries[channel, user] = callback
	
	async def register_reaction_query(self, message, callback, *options):
		# reactions = []
		for option in options:
			await message.add_reaction(option)
		# reactions.append()
		self._reaction_queries[message] = callback
	
	@as_event
	async def on_message(self, message):
		if message.author == self.user:
			return
		
		key = (message.channel, message.author)
		if key in self._message_queries:
			out = await self._message_queries[key](message)
			if out is not None:
				del self._message_queries[key]
		
		await self.process_commands(message)
	
	
	@as_event
	async def on_reaction_add(self, reaction, user):
		if user == self.user:
			return
		
		key = reaction.message
		if key in self._reaction_queries:
			out = await self._reaction_queries[key](reaction, user)
			if out is not None:
				del self._reaction_queries[key]
	
	
	def _insufficient_permissions(self, user):
		return str(user) not in self.admins
	
	
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
		
	
	@as_command('checkpoint')
	async def on_checkpoint(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		self.checkpoint()
		await ctx.send(f'Bot state has been saved.')
	
			
		

