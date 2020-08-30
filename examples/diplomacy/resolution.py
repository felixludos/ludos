


orders = {'move', 'hold', 'convoy', 'support'}

move = {'player', 'type', 'loc', 'target', 'use_convoy'}
hold = {'player', 'type', 'loc'}
support = {'player', 'type', 'loc', 'start', 'target'}
convoy = {'player', 'type', 'loc', 'start', 'target'}

unit = {'type', 'loc', 'player'}

tile = {'type', 'name', 'neighbors', 'unit', 'sc'} # optional for rendering {x, y, x2, y2, xa, ya}

# world is list of tiles
# NOTE: tile names may not end in -ec, -sc, -wc, or -nc (those are used for coasts)

def audit_world(world):
	raise NotImplementedError

def render():
	raise NotImplementedError

def _remove_coast(name):
	if _is_coast(name):
		return name[:-3]

def _is_coast(name):
	return name.endswith('-ec') or name.endswith('-sc') \
		or name.endswith('-wc') or name.endswith('-nc')

def _fix_coast(name, options):
	
	if name in options:
		return None
	
	names = [name+suffix for suffix in ['-ec', '-sc', '-wc', '-nc']]
	
	for name in names:
		if name in options:
			return name

def _check_valid_move_orders(world, valid, invalid):
	raise NotImplementedError

def _move_unit(unit, dest, tiles):
	
	old = tiles[unit['loc']]
	if 'unit' in old:
		del old['unit']
	
	unit['loc'] = dest
	
	new = tiles[dest]
	if 'unit' in new:
		new['retreat'] = new['unit']
	
	new['unit'] = unit
	
	

# def _in_conflict(demand)

def resolve(orders, world):
	'''
	
	
	:param orders: list of all orders (from all players)
	:param world: list of all tiles
	:param units: optional list of all units
	:return: world after executing/resolving orders
	'''
	
	# region create convenience data
	
	tiles = {tile['name']:tile for tile in world}
	
	units = [tile['unit'] for tile in world if 'unit' in tile and tile['unit'] is not None]
	
	unit_locs = {unit['loc']:unit for unit in units}

	# endregion
	
	# region filter invalid commands
	
	valid = {_remove_coast(order['loc']):order for order in orders}
	
	valid = {}
	invalid = []
	
	for order in orders:
		
		name = order['loc']
		
		fixed = _fix_coast(name, unit_locs)
		if fixed is not None:
			name = fixed
			order['loc'] = name
		
		if name not in unit_locs or order['player'] != unit_locs[name]['player']: # player doesnt have a unit there
			order['reason'] = 'No unit owned by {} in {}'.format(order['player'], name)
			invalid.append(order)
			continue

		order['unit'] = unit_locs[name]

		if order['type'] == 'support' \
				and order['target'] not in tiles[order['loc']]['neighbors']: # support too far away
			order['reason'] = 'Cannot support {} from {}'.format(order['target'], order['loc'])
			invalid.append(order)
			continue
		
		base = _remove_coast(name)
		
		if order['type'] == 'move' and base == _remove_coast(order['target']): # moving in place
			order['reason']	= 'Cannot move in-place from {} to {}'.format(name, order['target'])
			invalid.append(order)
			continue
		
		if base in valid: # previous order to this loc was already given (replace existing one)
			old_order = valid[base]
			del old_order['base']
			old_order['reason'] = 'Superseded by a later order'
			invalid.append(old_order)
		
		order['base'] = base
		valid[base] = order
	
	# endregion
	
	completed = []
	failed = []
	
	unit_bases = {_remove_coast(loc):unit for loc, unit in unit_locs.items()}
	
	move_targets = {}
	for order in valid.values():
		if order['type'] == 'move':
			base = _remove_coast(order['target'])
			if base not in move_targets:
				move_targets[base] = []
			move_targets[base].append(order)
	
	# region uncontested moves
	
	moved = []
	
	for target, mvs in move_targets.items():
		if len(mvs) == 1 and target not in unit_bases:
			
			order = mvs[0]
			
			dest = order['target']
			
			unit = unit_bases[target]
			
			_move_unit(unit, dest, tiles)
			
			moved.append(target)
			
			pass
	
	# endregion
	
	# region failed support
	
	
	
	# endregion
	
	
	# region check valid move orders
	_check_valid_move_orders(world, valid, invalid)
	
	# endregion
	
	# region compute target demand
	
	moves = [order for order in valid.values() if order['type'] == 'move']
	
	demand = {_remove_coast(loc):1 for loc in unit_locs}
	for order in moves:
		demand[order['base']] -= 1
		demand[order['target']] += 1

	# endregion
	
	# region resolve conflicts
	
	

	# endregion
	
	# region move units
	
	
	
	pass
	
	
def build(orders, world):
	pass


