
from .. import tdict, tlist, tset
from ..core import GameStack, GamePhase


class TurnPhaseStack(GameStack): # tracks turn counter, inc when creating a TurnPhase
	
	def __init__(self):
		super().__init__()
		self.players = None
		self.counter = None
		self.turn_phases = tset()
		
	def __save__(self):
		pack = self.__class__._pack_obj
		data = super().__save__()
		
		data['players'] = pack(self.players)
		data['counter'] = pack(self.counter)
		data['turn_phases'] = pack(self.turn_phases)
		
		return data
		
	def __load__(self, data):
		unpack = self.__class__._unpack_obj
		
		TurnPhaseStack.__init__(self)
		
		self.players = unpack(data['players'])
		self.counter = unpack(data['counter'])
		self.turn_phases = unpack(data['turn_phases'])
		
		super().__load__(data)
		
	def register(self, cls, name=None, **props):
		if name is None:
			name = cls.__class__.__name__
		if issubclass(cls, TurnPhase):
			self.turn_phases.add(name)
		super().register(cls, name=name, **props)
		
	def reset(self, phases=None):
		self.counter = 0
		super().reset(phases=phases)
		
	def set_player_order(self, players):
		self.players = players
	
	def _process_turn(self, name, **kwargs):
		if 'player' not in kwargs and self.players is not None:
			n = self.players[self.counter % len(self.players)].name
			c = self.counter
			kwargs['player'] = self.players[self.counter % len(self.players)]
			self.counter += 1
		return kwargs
	
	def create(self, name, **kwargs):
		if name in self.turn_phases:
			kwargs = self._process_turn(name, **kwargs)
		return super().create(name, **kwargs)


class TurnPhase(GamePhase):
	def __init__(self, player=None, **info):
		super().__init__(**info)
		self.player = player











