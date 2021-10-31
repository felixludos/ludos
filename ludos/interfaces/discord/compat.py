
from omnibelt import get_printer, unspecified_argument
import omnifig as fig

prt = get_printer(__file__)

import discord
from discord.ext import commands


class OmniBot(fig.Cerifiable, fig.Configurable, commands.Bot):
	def __init__(self, A, command_prefix=unspecified_argument, description=unspecified_argument,
	             intents=unspecified_argument,
	             options=unspecified_argument, _req_kwargs=None, **kwargs):
		
		if command_prefix is unspecified_argument:
			command_prefix = A.pull('command-prefix', '.')
		
		if description is unspecified_argument:
			description = A.pull('description', None)
			
		if options is unspecified_argument:
			options = A.pull('options', {})
		
		if _req_kwargs is None:
			_req_kwargs = {}
		_req_kwargs.update({'command_prefix':command_prefix, 'description':description, **options})
		
		if intents is not unspecified_argument:
			_req_kwargs['intents'] = intents
		
		super().__init__(A, _req_kwargs=_req_kwargs)
		
		
	@staticmethod
	def as_command(name=None, **kwargs):
		def _as_command(fn):
			nonlocal name, kwargs
			fn._discord_command_kwargs = {'name':name, **kwargs}
			return fn
		return _as_command
	
	
	@staticmethod
	def as_event(fn):
		fn._discord_event_flag = True
		return fn

	
	def __certify__(self, A, cmds=None, **kwargs):
		if cmds is None:
			cmds = A.pull('commands', [])
		
		super().__certify__(A, **kwargs)
		
		events = []
		
		if A.pull('include-class-commands', True, silent=True):
			for key, val in self.__class__.__dict__.items():
				if hasattr(val, '_discord_command_kwargs'):
					cmds.append(commands.Command(getattr(self, key), **val._discord_command_kwargs))
				if hasattr(val, '_discord_event_flag'):
					events.append(getattr(self, key))
				# if isinstance(val, commands.Command):
				# 	cmds.append(val)
		
		for cmd in cmds:
			if not isinstance(cmd, commands.Command):
				cmd = commands.Command(**cmd)
			self.add_command(cmd)
		for event in events:
			self.event(event)

as_command = OmniBot.as_command
as_event = OmniBot.as_event


@fig.Component('disord-command')
class OmniCommand(fig.Cerifiable, fig.Configurable, commands.Command):
	def __init__(self, A, name=unspecified_argument, func=None, description=unspecified_argument,
	             _req_kwargs=None, **kwargs):
		
		if name is unspecified_argument:
			name = A.pull('name', None)
		
		if func is None:
			func = A.pull('func', getattr(self, '_'))
			
		if description is unspecified_argument:
			description = A.pull('description', None)

		if _req_kwargs is None:
			_req_kwargs = {}
		_req_kwargs.update(dict(name=name, func=func, description=description,))
		super().__init__(A, _req_kwargs=_req_kwargs, **kwargs)
	
	
	def _(self, *args, **kwargs):
		raise NotImplementedError



