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
	def __init__(self, A, admins=None, intents=unspecified_argument, **kwargs):
		
		if intents is unspecified_argument:
			intents = discord.Intents.default()
			intents.members = True
			
		if admins is None:
			admins = A.pull('admins', [])
		
		super().__init__(A, intents=intents, **kwargs)
		self.register_buffer('admins', set(admins))
		
		self._rng = random.Random()
		self._rng.seed(3)
		
		self._interfaces = {}
		self._queries = {}


	def _insufficient_permissions(self, user):
		return str(user) not in self.admins
	
	
	async def _create_channel(self, name, *members, reason=None, category=None,
	                          overwrites=None, private=False):
		if overwrites is None:
			overwrites = {}
			# admin_role = get(guild.roles, name="Admin")
			# overwrites = {
			# 	guild.default_role: discord.PermissionOverwrite(read_messages=False),
			# 	member: discord.PermissionOverwrite(read_messages=True),
			# 	admin_role: discord.PermissionOverwrite(read_messages=True)
			# }
			
		if name is None:
			assert False
			
		_matches = [c for c in self.guild.channels if c.name == name]
		if len(_matches):
			return _matches[0]
		
		if category is None:
			category = self.gameroom
			
		members = set(members)
		for member in self._players:
			if member in members:
				overwrites[member] = discord.PermissionOverwrite(send_messages=True, )
			else:
				overwrites[member] = discord.PermissionOverwrite(send_messages=False, view_channel=private)
		
		channel = await self.guild.create_text_channel(name, reason=reason, category=category,
		                                               overwrites=overwrites)
		return channel
		
	
	async def _setup_player(self, member):
		name = str(member.display_name)
		channel = await self._create_channel(f'{name}-interface', member, private=True,
		                     reason='To talk to the game bot (in secret)')
		await channel.send('Use this channel to talk to the game bot (in secret)')
		print(f'{name} is setup')
		self._interfaces[member] = channel
		return member


	async def on_ready(self):
		print(f'Logged on as {self.user}')
		
		self.guild = self.guilds[0]
		self.gameroom = [c for c in self.guild.channels if c.name == 'GameRoom'][0]
		
		# guild = self.guilds[0]
		# await guild.create_role(name='admin')
		
		_players = ['bobmax', 'felixludos']
		_members = {member.display_name: member for member in self.get_all_members()}
		self._players = [_members[player] for player in _players]
		for player in self._players:
			await self._setup_player(player)
		self.table = await self._create_channel('table', *self._players)
		
		msg = await self.table.send(f'Ready')
		await msg.add_reaction(self._accept_mark)
		await msg.add_reaction(self._reject_mark)
	
	
	@as_command('ping')
	async def on_ping(self, ctx):
		role = ' (admin)' if str(ctx.author) in self.admins else ''
		await ctx.send(f'Hello, {ctx.author.display_name}{role}')

	
	@as_command('checkpoint')
	async def on_checkpoint(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		self.checkpoint()
		await ctx.send(f'Bot state has been saved.')
	
	
	@as_event
	async def on_message(self, message):
		if message.author == self.user:
			return
		
		print(f'{message}')
		
	
	@as_event
	async def on_reaction_add(self, reaction, user):
		if user.bot:
			return
		
		print(f'{reaction} {user}')


	# Murder
	
	_board_rewards = {
		2: [None, 'membership', 'draw', 'kill', 'kill'], # TESTING
		
		5: [None, None, 'draw', 'kill', 'kill'],
		6: [None, None, 'draw', 'kill', 'kill'],
		
		7: [None, 'membership', 'pick', 'kill', 'kill'],
		8: [None, 'membership', 'pick', 'kill', 'kill'],
		
		9:  ['membership', 'membership', 'pick', 'kill', 'kill'],
		10: ['membership', 'membership', 'pick', 'kill', 'kill'],
	}
	
	_notify_murderer = False
	
	_accept_mark = '✅' # '✔️'
	_reject_mark = '❎' #'❌'
	
	_vote_yes = '👍'
	_vote_no = '👎'
	
	
	@as_command('start')
	async def on_start(self, ctx):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		
		num = len(self._players)
		if num not in self._board_rewards:
			await ctx.send(f'Wrong number of players: {num}')
			return
		
		acc = (num+1)//2 - 2
		roles = ['a cop']*(num-acc-1) + ['an accomplice']*acc + ['the murderer']
		self._rng.shuffle(roles)
		for player, role in zip(self._players, roles):
			player._role = role
		
		murderer = [player for player in self._players if player._role == 'the murderer'][0]
		accomplices = [player for player in self._players if player._role == 'an accomplice']
		
		msg = await self.table.send(f'There are {acc} accomplice/s and 1 murderer.')
		# await msg.add_reaction(self._accept_mark)
		# await msg.add_reaction(self._reject_mark)
		
		for player in self._players:
			role = player._role
			await self._interfaces[player].send(f'You are {role}.')
			if role == 'an accomplice':
				await self._interfaces[player].send(f'The murderer is {murderer.display_name}.')
			if role == 'an accomplice' or (role == 'the murderer' and self._notify_murderer):
				await self._interfaces[player].send('The accomplices are {}.'
				                            .format(', '.join(a.display_name for a in accomplices)))
			
		self.commissioner = self._rng.choice(self._players)
		await self.table.send(f'{self.commissioner.display_name} is the first '
		                      f'police commissioner candidate.')
		await self._interfaces[self.commissioner].send(f'Select the next candidate detective')
		
		
	# def _register_query(self, channel, user, **info):
	# 	self._queries[]


class Response:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)
		
		
	def _underlying_val(self):
		return self.channel, self.user
		
		
	def __eq__(self, other):
		return self._underlying_val() == other._underlying_val()
	
	
	def __hash__(self):
		return hash(self._underlying_val())
		
		
			
		

