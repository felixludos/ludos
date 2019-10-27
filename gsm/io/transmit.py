import sys, os
import requests
import urllib.parse

from werkzeug.routing import BaseConverter

class LstConverter(BaseConverter):

	@staticmethod
	def to_python(value):
		out = []
		for v in value.split('+'):
			try:
				out.append(int(v))
			except:
				out.append(v)
		return tuple(out)

	@staticmethod
	def to_url(values):
		return '+'.join(BaseConverter.to_url(value)
						for value in values)

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
	
	return out.json()


