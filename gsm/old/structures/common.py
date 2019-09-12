


def condensed_str(x): # for printing dicts
	if isinstance(x, dict):
		s = []
		for k in x.keys():
			if isinstance(k, dict):
				s.append('{...}')
			elif isinstance(k, list):
				s.append('[...]')
			else:
				s.append(str(k))
		return '{}({})'.format(type(x), ', '.join(s))
	elif isinstance(x, list):
		s = []
		for k in x:
			if isinstance(k, dict):
				s.append('{...}')
			elif isinstance(k, list):
				s.append('[...]')
			else:
				s.append(str(k))
		return '[{}]'.format(', '.join(s))
	return str(x)
