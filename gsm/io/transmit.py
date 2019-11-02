import sys, os
import requests
import urllib.parse
import multiprocessing as mp
from .registry import register_trans, get_interface

from werkzeug.routing import BaseConverter

class LstConverter(BaseConverter):

	@staticmethod
	def to_python(value):
		out = []
		for v in value.split('+'):
			out.append(v)
			# try:
			# 	out.append(int(v))
			# except:
			# 	out.append(v)
		return tuple(out)

	@staticmethod
	def to_url(values):
		return '+'.join(str(value) for value in values)

def create_dir(path):
	try:
		os.mkdir(path)
	except FileExistsError:
		pass


def send_msg(addr, *command, data=None):
	
	payload = []
	
	for c in command:
		if isinstance(c, (tuple,list)):
			payload.append(LstConverter.to_url(c))
		else:
			payload.append(c)
			
	route = urllib.parse.urljoin(addr, '/'.join(payload))
	
	kwargs = {}
	send_fn = requests.get
	if data is not None:
		kwargs['json'] = data
		send_fn = requests.post
	
	out = send_fn(route, **kwargs)
	
	try:
		return out.json()
	except Exception:
		return out.text


def worker_fn(in_q, out_q, interface_type, settings):
	
	interface = get_interface(interface_type)(**settings)
	
	while True:
		
		cmd, *data = in_q.get()
		
		cmds = {'ping', 'step', 'reset', 'set_player'}
		
		if cmd == 'kill':
			break
		
		elif cmd == 'ping':
			out =
	
	pass


# used by the host - each passive frontend has one transceiver to communicate.
class Transceiver(object):
	
	def __init__(self, host_addr):
		self.host_addr = host_addr
	
	def ping(self):
		return 'ping'
	
	def set_player(self, user, player):
		raise NotImplementedError
	
	def reset(self, user):
		pass
	
	def step(self, user, data=None):
		raise NotImplementedError
	
	def send_msg(self, *args, **kwargs):
		pass

class Process_Transceiver(Transceiver): # running the interface in a parallel process
	
	def __init__(self, host_addr, interface, **settings):
		super().__init__(host_addr)
		
		self.interface = interface
		self.settings = settings
		
		self.receive_q = mp.Queue()
		self.send_q = mp.Queue()
		
		self.proc = None
		self._restart_proc()
		
	def _restart_proc(self):
		if self.proc is not None:
			self.send_q.put(('kill',))
		self.proc = mp.Process(target=worker_fn,
		                       args=(self.receive_q, self.send_q, self.interface, self.settings))
		self.proc.start()
		
	
	
	pass

register_trans('proc', Process_Transceiver)

class Server_Transceiver(Transceiver): # requires that the server is already running
	
	
	
	pass


register_trans('http', Process_Transceiver)
