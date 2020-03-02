
from humpack import tset, tdict, tlist, pack_member, unpack_member
from ..mixins import Named, Typed, Jsonable, Transactionable, Packable, Pullable, Writable
from ..errors import MissingValueError
from ..io.registry import register_player_type
from ..util import jsonify, get_printer

prt = get_printer(__name__)

class GameManager(Transactionable, Packable, Pullable):
	
	def __init__(self, force_include_type=False, hide_name=False, ):
		
		super().__init__()
		
		self.force_player_type = force_include_type
		self.hide_name = hide_name
		
		self.players = tdict()
		self.players_list = tlist()
		self.meta_info = tdict()
		self._in_transaction = False
		
	def get_player_cls(self, player_type):
		return self.meta_info[player_type].cls
		
	def reset(self, ctrl):
		
		game_info = ctrl._view_info()
		types = game_info['player_types']
		
		default = None
		
		for name, info in types.items():
			self.meta_info[name] = tdict(info)
			if 'open' not in self.meta_info[name] or self.meta_info[name].open is None:
				self.meta_info[name].open = tset()
			
			if not self.hide_name:
				self.meta_info[name].open.add('name')
				
			if 'default' in info and info['default']:
				default = name
			
		if default is None:
			if len(self.meta_info) == 1:
				default = next(iter(self.meta_info))
			else:
				raise Exception('no default player type provided')
		
		self.default_player = default
		
		# by default only show player type if there is more than one type registered
		self.show_player_type = len(self.meta_info) > 1 or self.force_player_type

	def create(self, name, player_type=None, **props): # TODO: allow players to have req properties
		
		if player_type is None:
			player_type = self.default_player
		
		self.players[name] = self.get_player_cls(player_type)(name, **props)
		
		del self.players[name].obj_type
		if self.show_player_type:
			self.players[name].type = self.players[name].get_type()
		
		self.players_list.append(self.players[name])
		
	# def verify(self, name=None):
	#
	# 	todo = self.players.keys() if name is None else [name]
	#
	# 	for name in todo:
	# 		p = self.players[name]
	# 		for req in self.req:
	# 			if req not in p:
	# 				raise MissingValueError(p.get_type(), req, *self.req)
		
		
	def __pack__(self):
		
		data = {}
		
		data['players'] = pack_member(self.players)
		data['req'] = pack_member(self.req)
		data['open'] = pack_member(self.open)
		data['_in_transaction'] = pack_member(self._in_transaction)
		data['meta_info'] = pack_member(self.meta_info)
		data['default_player'] = pack_member(self.default_player)
		
		return data
	
	def __unpack__(self, data):
		
		self.players = unpack_member(data['players'])
		self.players_list = tlist(self.players.values())
		self.req = unpack_member(data['req'])
		self.open = unpack_member(data['open'])
		self._in_transaction = unpack_member(data['_in_transaction'])
		self.meta_info = unpack_member(data['meta_info'])
		self.default_player = unpack_member(data['default_player'])
		
		# self.verify() # TODO: maybe enforce req upon load
	
	def begin(self):
		if self.in_transaction():
			return
			
		self._in_transaction = True
		self.players.begin()
		self.players_list.begin()
		self.meta_info.begin()
		
	def in_transaction(self):
		return self._in_transaction
		
	def commit(self):
		if not self.in_transaction():
			return

		self._in_transaction = False
		self.players.commit()
		self.players_list.commit()
		self.meta_info.commit()
		
	def abort(self):
		if not self.in_transaction():
			return
		
		self._in_transaction = False
		self.players.abort()
		self.players_list.abort()
		self.meta_info.abort()
		
	def pull(self, player=None):
		players = {}
		
		for name, p in self.players.items():
			open_keys = self.meta_info[p.get_type()].open
			if player is None or player != name:
				players[name] = {k: jsonify(v) for k, v in p.items() if k in open_keys}
			else:
				players[name] = {k: jsonify(v) for k, v in p.items() if k[0] != '_'}
		
		return players
	
	def __getitem__(self, item):
		if item in self.players:
			return self.players[item]
		return self.players_list[item]
	
	def __contains__(self, item):
		return item in self.players
	
	def __iter__(self):
		return iter(self.players_list)
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
	
	def __init_subclass__(cls, game=None, name=None, open=None, req_manager=None, obj_type=None, is_default=False,
	                      **kwargs):
		
		if obj_type is None:
			if name is not None:  # acts as an alias to obj_type
				obj_type = name
			else:
				prt.warning('No obj_type provided for {}'.format(cls.__name__))
				obj_type = cls.__name__
		
		super().__init_subclass__(obj_type=obj_type, **kwargs)
		
		if req_manager is not None:
			cls._req_manager = req_manager
			
		if game is not None:
			register_player_type(game=game, cls=cls, open=open, default=is_default)
	
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


