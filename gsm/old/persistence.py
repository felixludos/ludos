import yaml
# from .structures import adict, xset, idict, tdict, tset, tlist

def collate(raw, remove_space=True, transactionable=True):
	dicttype, settype, listtype = adict, xset, list
	if transactionable:
		dicttype, settype, listtype = tdict, tset, tlist
	if isinstance(raw, dict):
		return dicttype((collate(k, remove_space=remove_space, transactionable=transactionable),
		                  collate(v, remove_space=remove_space, transactionable=transactionable))
		                 for k,v in raw.items())
	elif isinstance(raw, list):
		return listtype(collate(x, remove_space=remove_space, transactionable=transactionable)
		                for x in raw)
	elif isinstance(raw, tuple):
		return (collate(x, remove_space=remove_space, transactionable=transactionable)
		        for x in raw)
	elif isinstance(raw, set):
		return settype(collate(x, remove_space=remove_space, transactionable=transactionable)
		            for x in raw)
	elif isinstance(raw, str) and remove_space:
		return raw.replace(' ', '_')
	return raw

def uncollate(raw, with_id=True):
	if isinstance(raw, dict):
		if isinstance(raw, idict) and with_id:
			return dict((uncollate(k,with_id),uncollate(v,with_id))
						for k,v in raw.to_dict(with_id).items())
		return dict((uncollate(k,with_id),uncollate(v,with_id))
					for k,v in raw.items())
	elif isinstance(raw, list):
		return [uncollate(x,with_id) for x in raw]
	elif isinstance(raw, tuple):
		return (uncollate(x,with_id) for x in raw)
	elif isinstance(raw, set) and type(raw) != xset:
		return set(uncollate(x,with_id) for x in raw)
	# elif isinstance(raw, str):
	#     return raw.replace('_', ' ')
	return raw




def save(data, path):
	yaml.dump(uncollate(data), open(path,'w'),
			  default_flow_style=False)

def load(path):
	return collate(yaml.load(open(path, 'r'))) #, Loader=yaml.FullLoader))



