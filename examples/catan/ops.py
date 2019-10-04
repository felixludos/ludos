
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
	

def build_catan_map(G, hex_info, ports, number_info, RNG):
	
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
		del field.val
	
	hinums = number_info.hi
	
	options = tlist(f for f in G.fields if f.res != 'desert')
	assert len(options) == (len(number_info.hi) + len(number_info.reg)), 'not the right number of tiles'
	remaining = tset()
	
	for num in hinums:
		
		idx = RNG.randint(0, len(options)-1)
		
		f = options[idx]
		f.num = num
		
		options.remove(f)
		for n in f.neighbors:
			if n is not None and n in options:
				remaining.add(n)
				options.remove(n)
	
	remaining.update(options)
	
	regnums = number_info.reg
	RNG.shuffle(regnums)
	
	for f, num in zip(remaining, regnums):
		f.num = num


def build(C, bldname, player, loc):
	bld = C.table.create(bldname, loc=loc, owner=player.name)
	loc.color = player.color
	loc.player = player.name
	loc.building = bldname
	player.buildings[bldname].add(bld)
	
	reward = C.state.rewards[bldname]
	player.vps += reward
	
	msg = None
	if reward == 1:
		msg = ' (gaining 1 victory point)'
	if reward > 1:
		msg = ' (gaining {} victory points)'.format(msg)
	C.log.writef('{} builds {}{}', player, bld, '' if msg is None else msg)