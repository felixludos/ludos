
from functools import partial

from omnibelt import get_printer, unspecified_argument
import omnifig as fig

prt = get_printer(__file__)

import discord
from discord.ext import commands as command_util
from discord.ext import tasks as tasks_util


class OmniBot(fig.Certifiable, fig.Configurable, command_util.Bot):
	def __init__(self, command_prefix='.', description=None, intents=unspecified_argument,
	             options=unspecified_argument, _req_kwargs=None, **kwargs):
		if options is unspecified_argument:
			options = {}
		if _req_kwargs is None:
			_req_kwargs = {}
		_req_kwargs.update({'command_prefix':command_prefix, 'description':description, **options})
		
		if intents is not unspecified_argument:
			_req_kwargs['intents'] = intents
		
		super().__init__(**_req_kwargs)
		
		
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

	
	@staticmethod
	def as_loop(**kwargs):
		return tasks_util.loop(**kwargs)


	@classmethod
	def inherit_commands_events(cls):
		cmds, events = {}, {}
		for parent in cls.__bases__:
			if issubclass(parent, OmniBot):
				c, e = parent.inherit_commands_events()
				cmds.update(c)
				events.update(e)
		
		for key, val in cls.__dict__.items():
			if hasattr(val, '_discord_command_kwargs'):
				val._discord_command_kwargs['func'] = val
				val._discord_command_kwargs['_bind_func'] = True
				cmds[key] = val._discord_command_kwargs
			if hasattr(val, '_discord_event_flag'):
				events[key] = val
		
		return cmds, events
		
	
	def __certify__(self, A, commands=None, **kwargs):
		# events = []
		# if A.pull('include-class-commands', True, silent=True):
		
		cmds, events = self.inherit_commands_events()
		if commands is None:
			commands = A.pull('commands', {})
		cmds.update(commands)
		
		super().__certify__(A, **kwargs)
		
		for name, cmd in cmds.items():
			if not isinstance(cmd, command_util.Command):
				if cmd.get('_bind_func', False):
					cmd['func'] = cmd['func'].__get__(self, self.__class__)
				if '_bind_func' in cmd:
					del cmd['_bind_func']
				if 'name' not in cmd:
					cmd['name'] = name
				cmd = command_util.Command(**cmd)
			self.add_command(cmd)
		for event in events.values():
			event = event.__get__(self, self.__class__)
			self.event(event)
		
		return self


as_command = OmniBot.as_command
as_event = OmniBot.as_event
as_loop = OmniBot.as_loop



@fig.component('disord-command')
class OmniCommand(fig.Certifiable, fig.Configurable, command_util.Command):
	def __init__(self, name=None, func=None, description=None, _req_kwargs=None, **kwargs):
		
		if func is None:
			func = getattr(self, '_')
			
		if _req_kwargs is None:
			_req_kwargs = {}
		_req_kwargs.update(dict(name=name, func=func, description=description,))
		super().__init__(**_req_kwargs)
	
	
	# def _(self, *args, **kwargs):
	# 	raise NotImplementedError



