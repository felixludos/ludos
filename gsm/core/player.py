
from humpack import tset, tdict, tlist
from ..mixins import Named, Typed, Jsonable, Transactionable, Savable, Pullable, Writable
from ..signals import MissingValueError
from ..util import obj_jsonify

class GameManager(Transactionable, Savable, Pullable):
	
	def __init__(self, cls=None, req=[], open=[], hidden=[]):
		
		super().__init__()
		
		if cls is None:
			cls = GamePlayer
		
		self.player_cls = cls
		self.players = tdict()
		self.req = tset(req)
		self.open = tset(open)
		self.hidden = tset(hidden)
		self._in_transaction = False
		
	def register(self, name, **props):
		
		self.players[name] = self.player_cls(name, **props)
		self.verify(name)
		
	def verify(self, name=None):
		
		todo = self.players.keys() if name is None else [name]
		
		for name in todo:
			p = self.players[name]
			for req in self.req:
				if req not in p:
					raise MissingValueError(p.get_type(), req, *self.req)
		
		
	def __save__(self):
		pack = self.__class__._pack_obj
		
		data = {}
		
		data['players'] = pack(self.players)
		data['req'] = pack(self.req)
		data['hidden'] = pack(self.hidden)
		data['open'] = pack(self.open)
		data['_in_transaction'] = pack(self._in_transaction)
		data['player_cls'] = pack(self.player_cls)
		
		return data
	
	def __load__(self, data):
		unpack = self.__class__._unpack_obj
		
		self.players = unpack(data['players'])
		self.req = unpack(data['req'])
		self.open = unpack(data['open'])
		self.hidden = unpack(data['hidden'])
		self._in_transaction = unpack(data['_in_transaction'])
		self.player_cls = unpack(data['player_cls'])
		
		# self.verify() # TODO: maybe enforce req upon load
	
	def begin(self):
		if self.in_transaction():
			return
			self.commit()
			
		self._in_transaction = True
		self.players.begin()
		self.req.begin()
		self.hidden.begin()
		self.open.begin()
		
	def in_transaction(self):
		return self._in_transaction
		
	def commit(self):
		if not self.in_transaction():
			return

		self._in_transaction = False
		self.players.commit()
		self.hidden.commit()
		self.req.commit()
		self.open.commit()
		
	def abort(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		self.players.abort()
		self.hidden.abort()
		self.req.abort()
		self.open.abort()
		
	def pull(self, player=None):
		players = {}
		
		for name, p in self.players.items():
			if player is None or player != name:
				players[name] = {k: obj_jsonify(v) for k, v in p.items() if k in self.open}
			else:
				players[name] = {k: obj_jsonify(v) for k, v in p.items() if k not in self.hidden}
		
		return players
	
	def __getitem__(self, item):
		return self.players[item]
	
	def __contains__(self, item):
		return item in self.players
	
	def __iter__(self):
		return iter(self.players.values())
	def names(self):
		return self.players.keys()
	
	def keys(self):
		return self.players.keys()
	def values(self):
		return self.players.values()
	def items(self):
		return self.players.items()
	
	def __len__(self):
		return len(self.players)
	
	




class GamePlayer(Named, Typed, Jsonable, Writable, tdict):
	def __init__(self, name, obj_type=None, **props):
		if obj_type is None:
			obj_type = self.__class__.__name__
		super().__init__(name=name, obj_type=obj_type, **props)

	# def __eq__(self, other):
	# 	return other == self.name or other.name == self.name

	def __hash__(self):
		return hash(self.name)
	def __eq__(self, other):
		try:
			return self.name == other.name
		except AttributeError:
			return self.name == other
	def __ne__(self, other):
		return not self.__eq__(other)

	def jsonify(self):
		return {'_player':self.name}

	def get_text_type(self):
		return 'player'
	def get_text_val(self):
		return self.name
	def get_text_info(self):
		return {'obj_type':self.get_type()}


