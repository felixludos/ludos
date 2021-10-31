
from pathlib import Path
from omnibelt import unspecified_argument, create_dir, save_yaml, load_yaml
import omnifig as fig



class Interface(fig.Cerifiable, fig.Configurable):
	def __init__(self, A, root=unspecified_argument, **kwargs):
		if root is unspecified_argument:
			root = A.pull('path', fig.get_current_project().get_path()/'.data')
		super().__init__(A, **kwargs)
		
		self.root = Path(root) / self.interface_name
		create_dir(self.root)
		
		self._buffers = set()
	
	
	def __certify__(self, A, auto_load=None, **kwargs):
		
		if auto_load is None:
			auto_load = A.pull('auto-load', True)
		
		super().__certify__(A, **kwargs)
		
		if auto_load:
			for name in self._buffers:
				try:
					setattr(self, name, self.load_data(name))
				except FileNotFoundError:
					pass
		
		
	def register_buffer(self, name, data):
		self._buffers.add(name)
		setattr(self, name, data)
	
	
	def __init_subclass__(cls, name=None, **kwargs):
		super().__init_subclass__(**kwargs)
		if name is None:
			name = cls.__name__
		cls.interface_name = name
		
	
	def checkpoint(self):
		for name in self._buffers:
			self.store_data(name, getattr(self, name))
	
	
	def store_data(self, name, data, root=None):
		if root is None:
			root = self.root
		save_yaml(data, root/f'{name}.yaml')


	def load_data(self, name, root=None):
		if root is None:
			root = self.root
		return load_yaml(root/f'{name}.yaml')



