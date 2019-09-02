


class Named(object):
	
	def __init__(self, name, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.name = name
	
	def __str__(self):
		return self.name

class Typed(object):
	def __init__(self, obj_type, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.obj_type = obj_type
	
	def get_type(self):
		return self.obj_type
