

from ... import tdict, tlist, tset
from ... import GameObject
from ._grid_util import quadgrid as _quadgrid


def QuadGrid(GameObject):
	pass

def QuadField(GameObject):
	pass

def QuadEdge(GameObject):
	pass

def QuadCorner(GameObject):
	pass


def make_quadgrid(rows, cols, table=None,
             enable_edges=False, enable_corners=False,
             
             grid_obj_type=None, field_obj_type=None,
             edge_obj_type=None, corner_obj_type=None):
	
	raw = _quadgrid(rows, cols)
	
	# fields
	if table is not None and field_obj_type is None:
		table.register_obj_type(obj_cls=QuadField)
		field_obj_type = 'QuadField'
	
	fields = tdict()
	for fid in raw.fields:
		f = raw.objects[fid]
		
		if table is None:
			obj = tdict(obj_type='field', _id=f.id,
		                   row=f.row, col=f.col,
		                   neighbors=f.fields)
		else:
			obj = table.create(obj_type=field_obj_type,
			                   
			                   row=f.row, col=f.col,
			                   neighbors=f.fields,
			                   )
		
		if enable_edges:
			obj.edges = f.edges
		
		if enable_corners:
			obj.corners = f.corners
		
		f.obj_id = obj._id
		
		fields[obj._id] = obj
		
	
	# edges
	edges = tdict()
	if enable_edges:
		if table is not None and edge_obj_type is None:
			table.register_obj_type(obj_cls=QuadEdge)
			edge_obj_type = 'QuadEdge'
		
		for eid in raw.edges:
			e = raw.objects[eid]
			
			if table is None:
				obj = tdict(obj_type='edge', _id=e.id,
				            fields=e.fields)
			else:
				obj = table.create(obj_type=edge_obj_type,
				
				                   fields=e.fields,
				                   )
			
			if enable_corners:
				obj.corners = e.corners
			
			e.obj_id = obj._id
			
			edges[obj._id] = obj
	
	# corners
	corners = tdict()
	if enable_corners:
		if table is not None and corner_obj_type is None:
			table.register_obj_type(obj_cls=QuadCorner)
			corner_obj_type = 'QuadCorner'
		
		for cid in raw.corners:
			c = raw.objects[cid]
			
			if table is None:
				obj = tdict(obj_type='corner', _id=c.id,
				            fields=c.fields)
			else:
				obj = table.create(obj_type=corner_obj_type,
				
				                   fields=c.fields,
				                   )
			
			if enable_edges:
				obj.edges = c.edges
			
			c.obj_id = obj._id
			
			corners[obj._id] = obj
			
	else:
		for fid in raw.fields:
			f = raw.objects[fid]
			del f.corners
		if 'edges' in raw:
			for eid in raw.edges:
				e = raw.objects[eid]
				del e.corners
		del raw.corners
	
	# create grid
	if table is not None:
		if grid_obj_type is None:
			table.register_obj_type(obj_cls=QuadGrid)
			grid_obj_type = 'QuadGrid'
		
		grid = table.create(obj_type=grid_obj_type,
		                    fields=fields)
	else:
		grid = tdict(obj_type='grid',
		             fields=fields)
	
	# connect fields
	for f in fields.values():
		
		f.neighbors = tlist((fields[raw.objects[n].obj_id] if n is not None else n)
		                    for n in f.neighbors)
		
		if len(edges):
			f.edges = tlist((edges[raw.objects[e].obj_id] if e is not None else e)
		                    for e in f.edges)
			
		if len(corners):
			f.corners = tlist((corners[raw.objects[c].obj_id] if c is not None else c)
		                    for c in f.corners)

	# connect edges
	if len(edges):
		for e in edges.values():
			e.fields = tlist((fields[raw.objects[f].obj_id] if f is not None else f)
		                    for f in e.fields)
			
			if len(corners):
				e.corners = tlist((corners[raw.objects[c].obj_id] if c is not None else c)
			                    for c in e.corners)

		grid.edges = edges

	# connect corners
	if len(corners):
		for c in corners.values():
			c.fields = tlist((fields[raw.objects[f].obj_id] if f is not None else f)
			                 for f in c.fields)
			
			if len(edges):
				c.edges = tlist((edges[raw.objects[e].obj_id] if e is not None else e)
				                for e in c.edges)
	
		grid.corners = corners
	
	return grid



