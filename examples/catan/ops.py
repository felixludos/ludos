
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
		e = get_next(c.edges, e)
		c = get_next(e.corners, c)
		
	return corners
	

def build_catan_map(G, hex_info, ports, RNG):
	
	start_field = None
	for field in G.fields:
		if field.val == 'A':
			start_field = field
	assert start_field is not None, 'could not find the start field'
	
	outside = get_outside_corners(start_field)
	
	for idx, port_type in ports.items():
		outside[idx].port = port_type
		
	# set hex types
	hextypes = tlist()
	for res, num in hex_info.items():
		hextypes.extend([res]*num)
	
	RNG.shuffle(hextypes)
	
	for field, hextype in zip(G.fields, hextypes):
		field.res = hextype
	
	hinums = tlist([6]*2 + [8]*2)
	
	options = tlist(G.fields)
	remaining = tset()
	
	for num in hinums:
		
		idx = RNG.randint(0, len(options)-1)
		
		f = options[idx]
		f.num = num
		
		options.remove(f)
		for n in f.neighbors:
			if n is not None and n not in remaining:
				remaining.add(n)
				options.remove(n)
	
	remaining.update(options)
	
	regnums = tlist([3, 4, 5, 9, 10, 11] * 2 + [2, 12])
	RNG.shuffle(regnums)
	
	for f, num in zip(remaining, regnums):
		f.num = num


