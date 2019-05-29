
from ..structures import TransactionableObject, tdict, tlist, tset


class GameTable(TransactionableObject):
	
	def __init__(self):
		super().__init__(self)
		
		self.objects = tdict()
		
		self.reset()
	
	def reset(self):
		self.created = tdict()
		self.updated = tdict()
		self.removed = tdict()
	
	def __getitem__(self, item):
		return self.objects[item]
	
	def __setitem__(self, key, value):
		self.objects[key] = value
		if key in self.objects:
			self.updated[key] = value
		else:
			self.created[key] = value
	
	def __delitem__(self, key):
		self.removed[key] = self.objects[key]
		del self.objects[key]

