
from ..basic_containers import tdict, tlist, tset
from ..mixins import Named, Typed, Transactionable, Savable, Pullable, Writable
from ..signals import MissingValueError
from .object import obj_jsonify

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
		
		
	def __save(self):
		pack = self.__class__.__pack
		
		data = {}
		
		data['players'] = pack(self.players)
		data['req'] = pack(self.req)
		data['hidden'] = pack(self.hidden)
		data['open'] = pack(self.open)
		data['_in_transaction'] = pack(self._in_transaction)
		data['player_cls'] = pack(self.player_cls)
		
		return data
	
	@classmethod
	def __load(cls, data):
		unpack = cls.__unpack
		
		self = cls()
		self.players = unpack(data['players'])
		self.req = unpack(data['req'])
		self.open = unpack(data['open'])
		self.hidden = unpack(data['hidden'])
		self._in_transaction = unpack(data['_in_transaction'])
		self.player_cls = unpack(data['player_cls'])
		
		# self.verify() # TODO: maybe enforce req upon load
		
		return self
	
	def begin(self):
		if self.in_transaction():
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
		
		for name, p in self.players:
			if player is None or player == name:
				players[name] = {k:obj_jsonify(v) for k, v in p.items() if k not in self.hidden}
			else:
				players[name] = {k:obj_jsonify(v) for k,v in p.items() if k in self.open}
				
		return players
	
	def __getitem__(self, item):
		return self.players[item]
	
	def __contains__(self, item):
		return item in self.players
	
	def names(self):
		return list(self.players.keys())




class GamePlayer(Named, Typed, Writable, tdict):
	def __init__(self, name, **props):
		super().__init__(name=name, obj_type=self.__class__.__name__, **props)

	# def __eq__(self, other):
	# 	return other == self.name or other.name == self.name

	def get_text_type(self):
		return 'player'
	def get_text_val(self):
		return self.name


