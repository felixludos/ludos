
import numpy as np


class ParityError(Exception):
	def __init__(self):
		super().__init__('Inconsistent spacing')

class RegistryError(Exception):
	def __init__(self, name):
		super().__init__('grid type "{}" already exists'.format(name))

_adj_y = {
	'hex': np.array([1, 2, 1, -1, -2, -1]),
	'quad': np.array([0, 1, 0, -1]),
	'octa': np.array([0, 1, 1, 1, 0, -1, -1, -1])
}

_adj_x = {
	'hex': np.array([-1, 0, 1, 1, 0, -1]),
	'quad': np.array([-1, 0, 1, 0]),
	'octa': np.array([-1, -1, 0, 1, 1, 1, 0, -1])
}

_edge_ninds = {
	'hex': lambda i: [i],
	'quad': lambda i: [i],
	'octa': None, # impossible
}
_edge_xinds = {
	'hex': lambda i: [( i +3 ) %6],
	'quad': lambda i: [( i +2 ) %4],
	'octa': None,
}
_edge_order = {
	'hex': lambda i: [1 ,0] if i < 3 else [0 ,1],
	'quad': lambda i: [1 ,0] if i < 2 else [0 ,1],
	'octa': None,
}

_corner_ninds = {
	'hex': lambda i: [( i -1 ) %6, i],
	'quad': None, # impossible
	'octa': lambda i: [ 2 *i, 2* i + 1, (2 * i + 2) % 8],
}
_corner_xinds = {
	'hex': lambda i: [(i + 2) % 6, (i - 2) % 6],
	'quad': None,
	'octa': lambda i: [(i + 1) % 4, (i + 2) % 4, (i + 3) % 4],
}
_corner_order = {
	'hex': lambda i: [1, 2, 0] if i == 1 or i == 2 else ([2, 0, 1] if i == 0 or i == 5 else [0, 1, 2]),
	'quad': None,
	'octa': lambda i: [0, 1, 2, 3],
}


def _add_subelement(field, fields, get_ID, elms, typ,
                    ninds, xinds, orders,
                    group_name=None, N=None):
	if group_name is None:
		group_name = typ + 's'
	
	if N is None:
		N = len(field['neighbors'])
	
	if group_name not in field:
		field[group_name] = []
	
	# add all corners to this field
	for i in range(N):
		
		x = None  # element to be added
		
		# try finding existing/corresponding x in neighbors
		# flds, priority = [field.ID], [i] + xinds(i)
		flds = [field['ID']]
		for ni, j in zip(ninds(i), xinds(i)):
			
			n = field['neighbors'][ni]
			flds.append(n)
			
			if n is not None and group_name in fields[n] and fields[n][group_name][j] is not None:
				x = fields[n][group_name][j]
		
		order = np.array(flds)[orders(i)].tolist()
		# print(group_name, field.ID, i, flds, ord, order)
		
		if x is None:
			elm = dict(ID=get_ID(typ), type=typ, fields=order)
			elms[elm['ID']] = elm
			x = elm['ID']
		
		field[group_name].append(x)


_hex_edge_corner_idx = {  # idx of the edge to be added in the corner
	0: [2, 1],
	1: [1, 0],
	2: [2, 0],
	3: [2, 1],
	4: [1, 0],
	5: [2, 0],
}


def _connect_hex_idx(i):
	corner_idx = _hex_edge_corner_idx[i]
	if 0 < i < 4:
		return [i, (i + 1) % 6], corner_idx  # idx of the corner to the added to the edge
	return [(i + 1) % 6, i], corner_idx


def _connect_elements(field, edges, corners):  # only for hex
	
	for i, eid in enumerate(field['edges']):
		
		e = edges[eid]
		
		if 'corners' not in e:
			e['corners'] = []
			
			for cidx, eidx in zip(*_connect_hex_idx(i)):
				
				cid = field['corners'][cidx]
				c = corners[cid]
				
				if 'edges' not in c:
					c['edges'] = [None] * 3
				
				c['edges'][eidx] = e['ID']
				
				e['corners'].append(c['ID'])


def _create_grid(M, grid_type='quad',
                 wrap_rows=False, wrap_cols=False,
                 # enforce_connectivity=True,
                 enable_edges=False, enable_corners=False, enable_boundary=False,
                 # enable_boundary necessary for add/remove fields
                 **spec):
	assert grid_type != 'quad' or not enable_corners, 'not working'
	assert grid_type != 'octa' or not enable_edges, 'not working'
	
	# prep Ids
	ID_counters = {'field': 0, 'edge': 0, 'corner': 0}
	
	def get_ID(t):
		ID = ID_counters[t]
		ID_counters[t] += 1
		return '{}{}'.format(t, ID)
	
	if not isinstance(M, list):
		M = M.split('\n')
	
	# create grid
	rows = len(M)
	cols = len(M[0])
	for row in M:
		assert len(row) == cols, 'Input map is non-rectangular'
	grid = np.empty((rows, cols), dtype='object')
	
	fields = {}
	parity = None  # since hex maps have double coverage
	
	for r, row in enumerate(M):
		for c, val in enumerate(row):
			if val != ' ':
				f = dict(ID=get_ID('field'), type='field', val=val, row=r, col=c)
				grid[r, c] = f['ID']
				fields[f['ID']] = f
				
				if parity is None:
					parity = (r + c) % 2
				elif parity != (r + c) % 2:
					raise ParityError()
	
	# find neighbors (and borders)
	aX, aY = _adj_x[grid_type], _adj_y[grid_type]
	
	for r, c in np.ndindex(rows, cols):
		
		if grid[r, c] is None:
			continue
		
		f = fields[grid[r, c]]
		if f is None:
			continue
		
		iX, iY = r + aX, c + aY
		selX = (iX < 0) + (iX >= rows)
		iX %= rows
		selY = (iY < 0) + (iY >= cols)
		iY %= cols
		
		f['neighbors'] = grid[iX, iY]
		
		if not (wrap_rows or wrap_cols):
			sel = selX * 0
			
			if not wrap_rows:
				sel += selX
			if not wrap_cols:
				sel += selY
			
			sel = sel.astype(bool)
			
			f['neighbors'][sel] = None  # clear invalid neighbors
	
	# create edges
	edges = {}
	if enable_edges:
		for field in fields.values():
			_add_subelement(field, fields, get_ID, edges, 'edge',
			                _edge_ninds[grid_type], _edge_xinds[grid_type], _edge_order[grid_type])
	
	# create corners
	corners = {}
	if enable_corners:
		for field in fields.values():
			_add_subelement(field, fields, get_ID, corners, 'corner',
			                _corner_ninds[grid_type], _corner_xinds[grid_type], _corner_order[grid_type])
		
		if enable_edges:
			
			# connect edges and corners
			for field in fields.values():
				_connect_elements(field, edges, corners)
	
	# format final output
	info = dict(
		fields=fields,
		map=grid,
	
	)
	
	if len(edges):
		info['edges'] = edges
	if len(corners):
		info['corners'] = corners
	
	return info






