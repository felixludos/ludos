import sys, os
import traceback
import json
import requests
import urllib.parse
from queue import Queue, Empty
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


def send_http(addr, *command, data=None, timeout=None):
	
	payload = []
	
	for c in command:
		if isinstance(c, (tuple,list)):
			payload.append(LstConverter.to_url(c))
		else:
			payload.append(str(c))
			
	route = urllib.parse.urljoin(addr, '/'.join(payload))
	
	kwargs = {}
	send_fn = requests.get
	if data is not None:
		kwargs['json'] = data
		send_fn = requests.post
	
	out = send_fn(route, timeout=timeout, **kwargs)
	
	try:
		return out.json()
	except Exception:
		return out.text

def worker_fn(in_q, out_q, interface_type, users, settings):
	
	# print(interface_type, users, settings)
	
	interface = get_interface(interface_type)(*users, **settings)
	
	while True:
		
		cmd, *data = in_q.get()
		
		if cmd == 'kill':
			break
			
		try:
			out = interface.__getattribute__(cmd)(*data)
			out_q.put(out)
	
		except Exception as e:
			out_q.put(('Command failed:', cmd, data,
			           e.__class__.__name__, ''.join(traceback.format_exception(*sys.exc_info()))))
	
	pass


# used by the host - each passive frontend has one transceiver to communicate.
class Transceiver(object):
	
	def __init__(self, host_addr, timeout=5):
		self.host_addr = host_addr
		self.timeout = timeout
	
	def _transmit(self, cmd, *args, **kwargs):
		raise NotImplementedError # should not wait longer than self.timeout
	
	def ping(self):
		return self._transmit('ping')
	
	def set_player(self, user, player):
		return self._transmit('set_player', user, player)
	
	def reset(self, user):
		return self._transmit('reset', user)
	
	def step(self, user, status):
		return self._transmit('step', user, status)
	
	def save(self):
		return self._transmit('save')
	
	def load(self, data):
		return self._transmit('load', data)
	
	def send_msg(self, cmd, *args, **kwargs):
		return self._transmit(cmd, args, kwargs)

class Process_Transceiver(Transceiver): # running the interface in a parallel process
	
	def __init__(self, host_addr, interface, *users, timeout=5, **settings):
		super().__init__(host_addr, timeout=timeout)
		
		self.interface = interface
		self.settings = settings
		self.settings['host_addr'] = host_addr
		self.users = users
		
		self.receive_q = mp.Queue()
		self.send_q = mp.Queue()
		
		self.proc = None
		self._restart_proc()
		
	def _restart_proc(self):
		if self.proc is not None:
			self.send_q.put(('kill',))
		self.proc = mp.Process(target=worker_fn,
		                       args=(self.send_q, self.receive_q,
		                             self.interface, self.users, self.settings))
		self.proc.start()
	
	# def step(self, user, status):
	# 	return json.loads(self._transmit('step', user, json.loads(status)))
	
	def _transmit(self, *msg):
		
		self.send_q.put(msg)
		
		try:
			out = self.receive_q.get(timeout=self.timeout)
		except Empty:
			out = None
		
		return out

register_trans('proc', Process_Transceiver)

class Server_Transceiver(Transceiver): # requires that the server is already running
	
	def __init__(self, client_addr, host_addr, timeout=5):
		super().__init__(host_addr, timeout=timeout)
	
		self.client_addr = client_addr
		
	def _transmit(self, cmd, *msg):
		
		data = None
		if cmd == 'step':
			user, data = msg
			msg = user,
		elif cmd == 'load':
			data, = msg
			msg = ()
	
		return send_http(self.client_addr, cmd, *msg, data=data, timeout=self.timeout)
	
	pass


register_trans('http', Process_Transceiver)
