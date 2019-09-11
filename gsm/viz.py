
from .util import unjsonify

def _expand_actions(code):
	if isinstance(code, set) and len(code) == 1:
		return _expand_actions(next(iter(code)))
	
	if isinstance(code, str) or isinstance(code, int):
		return [code]
	
	# tuple case
	if isinstance(code, (tuple, list)):
		return list(product(*map(_expand_actions, code)))
	if isinstance(code, set):
		return chain(*map(_expand_actions, code))
	return code
def _flatten(bla):
	output = ()
	for item in bla:
		output += _flatten(item) if isinstance(item, (tuple, list)) else (item,)
	return output

def _decode_action_set(code):
	code = _expand_actions(code)
	return tset(map(_flatten, code))


def print_response(msg):
	
	msg = unjsonify(msg)
	
	if 'error' in msg:
		print('*** ERROR: {} ***'.format(msg.error.type))
		print(msg.error.msg)
		print('****************************')
		
		return msg.table, None
		
	else:
		pass

