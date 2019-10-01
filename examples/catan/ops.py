
from gsm import tset, tlist, tdict
from gsm.common.world import grid


def get_outside_corners(field): # start corner must be N of the field at seam "1"
	
	def get_next(options, prev):
		for x in options:
			if x is not None and x != prev and None in x.fields:
				return x
	
	start = field.corners[0]
	e = field.edges[0]
	
	x1, f, x2 = start.fields
	assert f == field and x1 is None and x2 is None, 'Not the right corner'
	
	corners = tlist([start])
	
	c = get_next(e.corners, start)
	while c != start:
		corners.append(c)
		e = get_next(c.edges, c)
		c = get_next(e.corners, e)
		
	return corners
	

def build_catan_map(M, hex_info, ports, RNG, table):
	
	G = grid.make_hexgrid(M, table=table,
	                      enable_corners=True, enable_edges=True)
	
	start_field = None
	for field in G.fields:
		if field.val == 'A':
			start_field = field
	assert start_field is not None, 'could not find the start field'
	
	outside = get_outside_corners(start_field)
	
	for idx, port_type in ports.items():
		outside[idx].port = port_type
		
	# TODO: hex info, hex numbers
	
	pass


