


COAST_NAMES = {
	'ec': 'Eastern Coast',
	'sc': 'Southern Coast',
	'wc': 'Western Coast',
	'nc': 'Northern Coast',
}



def separate_coasts(nodes, long_coasts=True):
	coasts = {}
	
	for ID, node in nodes.items():
		name = node['name']
		if 'dirs' in node:
			for c in node['dirs']:  # add coasts as separate nodes
				cname = COAST_NAMES[c] if long_coasts else f'({c.upper()})'
				coasts[f'{ID}-{c}'] = {'name': f'{name} {cname}', 'type': 'coast', 'coast-of': ID, 'dir':c}
			# node['coasts'] = [f'{ID}-{c}' for c in node['coasts']]
	
		elif node['type'] == 'coast':
			coasts[f'{ID}-c'] = {'name': f'{name} Coast', 'type': 'coast', 'coast-of': ID}
			# node['coasts'] = [f'{ID}-c']
	
	return coasts


def list_edges(raw_edges):
	
	full = []
	
	for edge_type, edge_group in raw_edges.items():
		for s, es in edge_group.items():
			for e in es:
				full.append({'start': s, 'end': e, 'type': edge_type})
				
	return full



