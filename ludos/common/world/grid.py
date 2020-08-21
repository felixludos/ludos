
import numpy as np
from ... import tdict, tlist, tset
from ... import GameObject, Array
from ._old_grid_util import quadgrid as _quadgrid
from ._grid_util import _create_grid

_neighbors = {
	'hex': {
		'NE':0,
		'E':1,
		'SE':2,
		'SW':3,
		'W':4,
		'NW':5,
	},
	'quad': {
		'N':0,
		'E':1,
		'S':2,
		'W':3,
	},
	'octa': {
		'N':0,
		'E':1,
		'S':2,
		'W':3,
	},
}

class Grid(GameObject):

	def __init__(self, fields, rows, cols, **other):
		super().__init__(fields=fields, rows=rows, cols=cols, **other)
		
		self.map = Array(np.empty((rows, cols), dtype='object'))
		
		for f in fields:
			self.map[f.row - 1, f.col - 1] = f


class Field(GameObject):  # TODO: add aliases/indexing
	pass


class Edge(GameObject):
	pass


class Corner(GameObject):
	pass


def _format_grid(raw, table=None,
             enable_edges=False, enable_corners=False,
             
             grid_obj_type=None, field_obj_type=None,
             edge_obj_type=None, corner_obj_type=None):
	# fields
	if table is not None and field_obj_type is None:
		table.register_obj_type(obj_cls=Field)
		field_obj_type = Field.__name__
	
	fields = tdict()
	for fid, f in raw['fields'].items():
		
		if table is None:
			obj = tdict(obj_type='field', _id=f['ID'],
			            row=f['row'], col=f['col'],
			            neighbors=f['neighbors'])
			
		else:
			obj = table.create(obj_type=field_obj_type,
			
			                   row=f['row'], col=f['col'],
			                   neighbors=f['neighbors'],
			                   )
			

		if 'val' in f:
			obj['val'] = f['val']
		
		if enable_edges:
			obj.edges = f['edges']
		
		if enable_corners:
			obj.corners = f['corners']
		
		f['obj_id'] = obj._id
		
		fields[obj._id] = obj
	
	# edges
	edges = tdict()
	if enable_edges:
		if table is not None and edge_obj_type is None:
			table.register_obj_type(obj_cls=Edge)
			edge_obj_type = Edge.__name__
		
		for eid, e in raw['edges'].items():
			if table is None:
				obj = tdict(obj_type='edge', _id=e['ID'],
				            fields=e['fields'])
			else:
				obj = table.create(obj_type=edge_obj_type,
				
				                   fields=e['fields'],
				                   )
			
			if enable_corners:
				obj.corners = e['corners']
			
			e['obj_id'] = obj._id
			
			edges[obj._id] = obj
	
	# corners
	corners = tdict()
	if enable_corners:
		if table is not None and corner_obj_type is None:
			table.register_obj_type(obj_cls=Corner)
			corner_obj_type = Corner.__name__
		
		for cid, c in raw['corners'].items():
			
			if table is None:
				obj = tdict(obj_type='corner', _id=c['ID'],
				            fields=c['fields'])
			else:
				obj = table.create(obj_type=corner_obj_type,
				
				                   fields=c['fields'],
				                   )
			
			if enable_edges:
				obj.edges = c['edges']
			
			c['obj_id'] = obj._id
			
			corners[obj._id] = obj
	
	else:
		for fid, f in raw['fields'].items():
			if 'corners' in f:
				del f['corners']
		if 'edges' in raw:
			for eid, e in raw['edges'].items():
				if 'corners' in e:
					del e['corners']
		if 'corners' in raw:
			del raw['corners']
	
	# create grid
	if table is not None:
		if grid_obj_type is None:
			table.register_obj_type(obj_cls=Grid)
			grid_obj_type = Grid.__name__
		
		grid = table.create(obj_type=grid_obj_type,
		                    fields=tset(fields.values()),
		                    rows=raw['rows'], cols=raw['cols'])
	else:
		grid = tdict(obj_type='grid',
		             fields=tset(fields.values()),
		             rows=raw['rows'], cols=raw['cols'])
	
	# connect fields
	for f in fields.values():
		
		f.neighbors = tlist((fields[raw['fields'][n]['obj_id']] if n is not None else n)
		                    for n in f['neighbors'])
		
		if len(edges):
			f.edges = tlist((edges[raw['edges'][e]['obj_id']] if e is not None else e)
			                for e in f['edges'])
		
		if len(corners):
			f.corners = tlist((corners[raw['corners'][c]['obj_id']] if c is not None else c)
			                  for c in f['corners'])
	
	# connect edges
	if len(edges):
		for e in edges.values():
			e.fields = tlist((fields[raw['fields'][f]['obj_id']] if f is not None else f)
			                 for f in e['fields'])
			
			if len(corners):
				e.corners = tlist((corners[raw['corners'][c]['obj_id']] if c is not None else c)
				                  for c in e['corners'])
		
		grid.edges = tset(edges.values())
	
	# connect corners
	if len(corners):
		for c in corners.values():
			c.fields = tlist((fields[raw['fields'][f]['obj_id']] if f is not None else f)
			                 for f in c['fields'])
			
			if len(edges):
				c.edges = tlist((edges[raw['edges'][e]['obj_id']] if e is not None else e)
				                for e in c['edges'])
		
		grid.corners = tset(corners.values())
	
	return grid


def make_quadgrid(rows, cols, table=None,
             enable_edges=False, enable_corners=False,
             
             grid_obj_type=None, field_obj_type=None,
             edge_obj_type=None, corner_obj_type=None):
	
	raw = _quadgrid(rows, cols)
	
	fields = {}
	
	for fid in raw.fields:
		fields[fid] = raw.objects[fid]
		fields[fid].ID = fields[fid].id
		fields[fid].neighbors = fields[fid].fields
		
	edges = {eid:raw.objects[eid] for eid in raw.edges}
	corners = {cid:raw.objects[cid] for cid in raw.corners}
	
	raw = {
		'fields': fields,
		'edges': edges,
		'corners': corners,
		'rows': raw.rows,
		'cols': raw.cols,
	}
	
	
	return _format_grid(raw, table=table,
             enable_edges=enable_edges, enable_corners=enable_corners,
             
             grid_obj_type=grid_obj_type, field_obj_type=field_obj_type,
             edge_obj_type=edge_obj_type, corner_obj_type=corner_obj_type)


def make_hexgrid(M, table=None,
                 wrap_rows=False, wrap_cols=False,
                 enable_edges=False, enable_corners=False,

                 grid_obj_type=None, field_obj_type=None,
                 edge_obj_type=None, corner_obj_type=None
                 ):
	
	assert not (wrap_cols or wrap_rows), 'not tested yet'
	
	raw = _create_grid(M, grid_type='hex',
	                  wrap_rows=wrap_rows, wrap_cols=wrap_cols,
	                  
	                  enable_corners=enable_corners, enable_edges=enable_edges,
	                  )
	
	raw['rows'], raw['cols'] = raw['map'].shape
	
	return _format_grid(raw, table=table,
	                    enable_edges=enable_edges, enable_corners=enable_corners,
	                    grid_obj_type=grid_obj_type, field_obj_type=field_obj_type,
	                    edge_obj_type=edge_obj_type, corner_obj_type=corner_obj_type,
	                    )

