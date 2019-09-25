

from ... import tdict, tlist, tset
from ... import GameObject
from ._grid_util import quadgrid as _quadgrid

def QuadGrid(GameObject):
	pass

def quadgrid(rows, cols, table,
             disable_edges=False, disable_corners=False,
             
             grid_obj_type=None, field_obj_type=None,
             edge_obj_type=None, corner_obj_type=None):
	
	
	raw = _quadgrid(rows, cols)
	
	
	if disable_edges:
		
		for fid in raw.fields:
			f = raw.objects[fid]
			
			del f.edges
			
		for cid in raw.corners:
			c = raw.objects[cid]
			
			del c.edges
			
	if disable_corners:
		
		for fid in raw.fields:
			f = raw.objects[fid]
			
			del f.corners
			
		for eid in raw.edges:
			e = raw.objects[eid]
			
			del e.corners
			
	



