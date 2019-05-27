# tdict - dicts allowing transactions (including nested tdicts)
from .arg_dict import adict
from .common import condensed_str
from .sets import xset
from wrapt import ObjectProxy
from itertools import chain

class AbortTransaction(Exception):
	pass

class Transactionable(object):
	
	def begin(self):
		raise NotImplementedError
	
	def in_transaction(self):
		raise NotImplementedError
	
	def commit(self):
		raise NotImplementedError
	
	def abort(self):
		raise NotImplementedError
	
	# def __enter__(self):
	# 	self._context = True
	# 	self.begin()
	#
	# def __exit__(self, type, *args):
	# 	self._context = False
	# 	if type is None:
	# 		self.commit()
	# 	else:
	# 		self.abort()
	# 	return None if type is None else type.__name__ == 'AbortTransaction'


class TransactionableObject(ObjectProxy, Transactionable):
	def __init__(self, original, iterations=None):
		
		super().__init__(original)
		
		if iterations is None:
			iterations = [lambda x: chain(x.__dict__.items())]
		self._self_iteration_fns = iterations if isinstance(iterations, list) else [iterations]
		
		assert original is not None, 'Cant create transactions for None'
		
		self._self_original = original
		self._self_transaction = None
		self._self_context = False
	
	def begin(self):
		if self.in_transaction():
			self.abort()
		self._self_transaction = self._self_original.copy()
		self.__wrapped__ = self._self_transaction
		
		for val in chain(*[itr_fn(self._self_transaction) for itr_fn in self._self_iteration_fns]):
			if isinstance(val, Transactionable):
				val.begin()
	
	def in_transaction(self):
		return self._self_transaction is not None
	
	def commit(self):
		if not self.in_transaction():
			return
		for val in chain(*[itr_fn(self._self_transaction) for itr_fn in self._self_iteration_fns]):
			if isinstance(val, Transactionable):
				val.commit()
		
		self._self_original = self._self_transaction
		
		self._self_transaction = None
		self.__wrapped__ = self._self_original
		
		if self._self_context:
			self.begin()
	
	def abort(self):
		if not self.in_transaction():
			return
		for val in chain(*[itr_fn(self._self_transaction) for itr_fn in self._self_iteration_fns]):
			if isinstance(val, Transactionable):
				val.abort()
		
		self._self_transaction = None
		self.__wrapped__ = self._self_original
		
		if self._self_context:
			self.begin()
	
	def __repr__(self):
		return self.__wrapped__.__repr__()
	
	def __str__(self):
		return self.__wrapped__.__str__()
	
	def __enter__(self):
		self._self_context = True
		self.begin()
	
	def __exit__(self, type, *args):
		self._self_context = False
		if type is None:
			self.commit()
		else:
			self.abort()
		return None if type is None else type.__name__ == 'AbortTransaction'

def tdict(*args, **kwargs):
	return TransactionableObject(adict(*args, **kwargs), lambda x: iter(chain(x.keys(), x.values())))

def tlist(*args, **kwargs):
	return TransactionableObject(list(*args, **kwargs), lambda x: iter(x))

def tset(*args, **kwargs):
	return TransactionableObject(xset(*args, **kwargs), lambda x: iter(x))










# Old manual implementation for tdict

# class TransactionError(Exception):
# 	pass
#
#
# class UnfinishedTransactionError(Exception):
# 	pass
#
#
# class _DeleteItemFlag(object):
# 	pass
#
# class Transaction_Collection(object):
#
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
#
# 		self.__dict__['_transaction'] = None
# 		self.__dict__['_pending_len'] = 0
#
# 	def __len__(self):
# 		if self._transaction is None:
# 			return super().__len__()
# 		return self._pending_len
#
# 	def begin(self):
# 		raise NotImplementedError
# 	def commit(self):
# 		raise NotImplementedError
# 	def abort(self):
# 		raise NotImplementedError
# 	def in_transaction(self):
# 		raise NotImplementedError
#
# 	def __enter__(self):
# 		self.begin()
#
# 	def __exit__(self, type, *args):
# 		if type is None:
# 			self.commit()
# 		else:
# 			self.abort()
#
# class tdict_keysiterator(object):
# 	def __init__(self, table, pending):
# 		self._togo = set(super(tdict, table).keys())
# 		if pending is not None:
# 			self._togo.update(super(adict, pending).keys())
# 		self._togo = iter(self._togo)
# 		self._table = table
# 		self._pending = pending
#
# 	def __iter__(self):
# 		return self
#
# 	def __next__(self):
# 		k = None
# 		while k is None:
# 			k = next(self._togo)
# 			if self._pending is not None and k in self._pending:
# 				if self._pending[k] is _DeleteItemFlag:
# 					k = None
# 				else:
# 					return k
# 		return k
#
#
# class tdict_keys(object):
# 	def __init__(self, view, pending):
# 		self._view = view
# 		self._pending = pending
#
# 	def __iter__(self):
# 		return tdict_keysiterator(self._view, self._pending)
#
# 	def __repr__(self):
# 		return 'tdict_keys({})'.format(', '.join(repr(k) for k in iter(self)))
#
#
# class tdict_itemsiterator(object):
# 	def __init__(self, table, pending):
# 		self._togo = set(super(tdict, table).keys())
# 		if pending is not None:
# 			self._togo.update(super(adict, pending).keys())
# 		self._togo = iter(self._togo)
# 		self._table = table
# 		self._pending = pending
#
# 	def __iter__(self):
# 		return self
#
# 	def __next__(self):
# 		k = None
# 		while k is None:
# 			k = next(self._togo)
# 			if self._pending is not None and k in self._pending:
# 				if self._pending[k] is _DeleteItemFlag:
# 					k = None
# 				else:
# 					return k, self._pending[k]
# 		return k, self._table[k]
#
#
# class tdict_items(object):
# 	def __init__(self, view, pending):
# 		self._view = view
# 		self._pending = pending
#
# 	def __iter__(self):
# 		return tdict_itemsiterator(self._view, self._pending)
#
# 	def __repr__(self):
# 		return 'tdict_items({})'.format(', '.join('{}:{}'.format(repr(k), repr(v)) for k, v in iter(self)))
#
#
# class tdict_valuesiterator(object):
# 	def __init__(self, table, pending):
# 		self._togo = set(super(tdict, table).keys())
# 		if pending is not None:
# 			self._togo.update(super(adict, pending).keys())
# 		self._togo = iter(self._togo)
# 		self._table = table
# 		self._pending = pending
#
# 	def __iter__(self):
# 		return self
#
# 	def __next__(self):
# 		k = None
# 		while k is None:
# 			k = next(self._togo)
# 			if self._pending is not None and k in self._pending:
# 				if self._pending[k] is _DeleteItemFlag:
# 					k = None
# 				else:
# 					return self._pending[k]
# 		return self._table[k]
#
#
# class tdict_values(object):
# 	def __init__(self, view, pending):
# 		self._view = view
# 		self._pending = pending
#
# 	def __iter__(self):
# 		return tdict_valuesiterator(self._view, self._pending)
#
# 	def __repr__(self):
# 		return 'tdict_values({})'.format(', '.join(repr(v) for v in iter(self)))
#
#
# class tdict(dict):
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self.__dict__['_transaction'] = None
# 		self.__dict__['_pending_len'] = 0
#
#
#
# 	def __getattr__(self, key):
# 		# try:
# 		# 	return super().__getattr__(key)
# 		# except:
# 		# 	return self.__getitem__(key)
# 		return self.__getitem__(key)
#
# 	def __setattr__(self, key, value):
# 		if key in self.__dict__:
# 			self.__dict__[key] = value
# 			return
# 		return self.__setitem__(key, value)
#
# 	def __delattr__(self, item):
# 		return self.__delitem__(item)
#
# 	def __contains__(self, key):
# 		if self._transaction is not None:
# 			return key not in self._transaction or self._transaction[key] != _DeleteItemFlag
# 		return super().__contains__(key)
#
# 	def __getitem__(self, key):
# 		if self._transaction is not None and key in self._transaction and self._transaction[key] != _DeleteItemFlag:
# 			return self._transaction[key]
# 		return super().__getitem__(key)
#
# 	def __setitem__(self, key, value):
# 		if self._transaction is not None:
# 			if key not in self._transaction and not super().__contains__(key):
# 				self._pending_len += 1
# 			self._transaction[key] = value
# 			return
# 		super().__setitem__(key, value)
#
# 	def __delitem__(self, key):
# 		if self._transaction is not None:
# 			if super().__contains__(key):
# 				self._transaction[key] = _DeleteItemFlag
# 				return
# 			del self._transaction[key]
# 			return
# 		super().__delitem__(key)
#
# 	def __iter__(self):
# 		return iter(self.keys())
#
# 	def keys(self):
# 		return tdict_keys(self, self._transaction)
#
# 	def values(self):
# 		return tdict_values(self, self._transaction)
#
# 	def items(self):
# 		return tdict_items(self, self._transaction)
#
# 	def __getstate__(self):
# 		return super().__getstate__()
#
# 	def copy(self):
# 		copy = tdict(self.items())
# 		if self._transaction is not None:
# 			copy._transaction = self._transaction.copy()
# 		return copy
#
# 	def __str__(self):
# 		items = []
# 		for k, v in self.items():
# 			items.append('{}:{}'.format(str(k), condensed_str(v)))
# 		return 'adict({})'.format(', '.join(items))
#
# 	def __repr__(self):
# 		return '{' + ', '.join('{}:{}'.format(repr(k), repr(v)) for k, v in self.items()) + '}'
#
# 	def begin(self):
# 		if self._transaction is not None:
# 			self.abort()  # automatically abort unfinished transaction
# 		# raise UnfinishedTransactionError('Commit or Abort current transaction before beginning a new one')
#
# 		self._pending_len = len(self)
# 		self._transaction = adict()
#
# 		for v in self.values():
# 			if isinstance(v, tdict):
# 				v.begin()
#
# 	def in_transaction(self):
# 		return self._transaction is not None
#
# 	def commit(self):
#
# 		if self._transaction is None:
# 			return True
#
# 		for v in self.values():
# 			if isinstance(v, tdict):
# 				v.commit()
#
# 		changes = self._transaction
# 		self._transaction = None
#
# 		for k, v in changes.items():
# 			if v is _DeleteItemFlag:
# 				del self[k]
# 			else:
# 				self[k] = v
#
# 		return True
#
# 	def abort(self):
#
# 		if self._transaction is None:
# 			return True
#
# 		for v in self.values():
# 			if isinstance(v, tdict):
# 				v.abort()
#
# 		self._transaction = None
#
# 		return True

