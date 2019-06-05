
from ..structures import tdict, tset, tlist


class GameObject(tdict):
	
	def __init__(self, obj_type, table=None, visible=None):
		super().__init__(obj_type=obj_type, visible=visible, _tracker=self)
		
		self.__dict__['_table'] = table
		
	def signal(self):
		if self._table is not None:
			self._table.update(self._id, self)
	
	def set_id(self, ID):
		if self._table is not None:
			self._table.remove(self._id)
		
		self._id = ID
		
		if self._table is not None:
			self._table.update(self._id, self)
		
	
