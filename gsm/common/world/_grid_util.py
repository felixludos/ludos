from ...basic_containers import tdict, tlist, tset

dhelp = {}
idCounters = {'field': 0, 'corner': 0, 'edge': 0, 'other': 0}

def getId(o):
	global idCounters
	if 'obj_type' in o and o.obj_type in idCounters:
		idCounters[o.obj_type] += 1
		prefix = o.obj_type[0]
		return prefix + str(idCounters[o.obj_type])
	else:
		prefix = 'o'
		idCounters['other'] += 1
		return prefix + str(idCounters['other'])

def calc_hex_col_array(rows, cols):
	colarr = []  #how many cols in each row
	for i in range(rows):
		colarr.append(cols)
		if i < (rows - 1) / 2:
			cols += 1
		else:
			cols -= 1
	return colarr

def quadgrid(rows, cols):
	global idCounters
	dhelp = {}
	idCounters = {'field': 0, 'corner': 0, 'edge': 0, 'other': 0}
	h = tdict()
	h.objects = tdict()
	h.obj_type = 'quadgrid'
	h.id = getId(h)
	h.topcols = cols  # cols in top row
	h.colarr = [cols] * rows
	h.maxcols = cols
	h.rows = rows
	h.cols = cols
	h.fields = []
	h.corners = []
	h.edges = []
	imiddleRow = (rows - 1) / 2
	indexRow = [-1, 0, 0, -1]  #NE node is f.corners[0]
	indexCol = [0, 0, -1, -1]
	#fields
	for irow in range(len(h.colarr)):
		for icol in range(h.colarr[irow]):
			#field________________
			field = tdict()
			field.obj_type = 'field'
			field.id = getId(field)
			field.row = irow + 1
			field.col = icol + 1
			field.edges = [None] * 4
			field.fields = [None] * 4
			field.corners = [None] * 4
			h.objects[field.id] = field
			h.fields.append(field.id)

	#nodes________________
	for fid in h.fields:
		field = h.objects[fid]
		#nodes field is irow+1,icol+1
		for inode in range(4):
			#make node idByRC
			nrow = field.row + indexRow[inode]
			ncol = field.col + indexCol[inode]
			irc = 'n' + '-' + str(nrow) + '_' + str(ncol)
			node = None
			if irc in dhelp:
				node = dhelp[irc]
			else:
				node = tdict()
				node.obj_type = 'corner'
				node.id = getId(node)
				node.row = nrow
				node.col = ncol
				node.edges = [None, None, None, None]
				node.fields = [None, None, None, None]
				h.corners.append(node.id)
				dhelp[irc] = node
				h.objects[node.id] = node
			#fields of nodes
			if inode == 0:
				node.fields[2] = field.id
			elif inode == 1:
				node.fields[3] = field.id
			elif inode == 2:
				node.fields[0] = field.id
			elif inode == 3:
				node.fields[1] = field.id
			field.corners[inode] = node.id

	#edges________________
	for fid in h.fields:
		field = h.objects[fid]
		#field indices is irow+1,icol+1
		for i in range(4):
			inode = (i + 3) % 4
			in1 = inode
			in2 = (inode + 1) % 4
			n1 = h.objects[field.corners[in1]]
			n2 = h.objects[field.corners[in2]]

			startNode = n1
			if n1.row > n2.row:
				startNode = n2
			if n1.row == n2.row and n1.col > n2.col:
				startNode = n2
			endNode = n2 if startNode == n1 else n1

			irc = 'e' + str(startNode.id) + '_' + str(endNode.id)
			edge = None
			if irc in dhelp:
				edge = dhelp[irc]
			else:
				edge = tdict()
				edge.obj_type = 'edge'
				edge.id = getId(edge)
				edge.row = startNode.row
				edge.col = startNode.col
				edge.fields = [None, None]
				edge.leftField = None
				edge.rightField = None
				edge.topField = None
				edge.bottomField = None
				edge.crossField = None
				edge.corners = [startNode.id, endNode.id]
				edge.startNode = startNode.id
				edge.endNode = endNode.id
				#add this edge id to each node's edges list ok
				if inode == 0:
					n1.edges[2] = edge.id
					n2.edges[0] = edge.id
				elif inode == 1:
					n1.edges[3] = edge.id
					n2.edges[1] = edge.id
				elif inode == 2:
					n1.edges[0] = edge.id
					n2.edges[2] = edge.id
				elif inode == 3:
					n1.edges[1] = edge.id
					n2.edges[3] = edge.id
				#add edge to board, dhelp
				h.edges.append(edge.id)
				dhelp[irc] = edge
				h.objects[edge.id] = edge
			if inode == 0:
				edge.fields[1] = field.id
				edge.leftField = field.id
			elif inode == 1:
				edge.fields[0] = field.id
				edge.topField = field.id
			elif inode == 2:
				edge.fields[0] = field.id
				edge.rightField = field.id
			elif inode == 3:
				edge.fields[1] = field.id
				edge.bottomField = field.id
			field.edges[(inode + 1) % 4] = edge.id

	#add fields of fields ok
	for fid in h.fields:
		f = h.objects[fid]
		for i in range(4):
			if not f.edges[i]:
				continue
			e = h.objects[f.edges[i]]
			for f1 in e.fields:
				if f1 and f1 != fid:
					f.fields[i] = f1
	return h

def hexgrid(rows, cols):
	global idCounters
	dhelp = {}
	idCounters = {'field': 0, 'corner': 0, 'edge': 0, 'other': 0}
	h = tdict()
	h.objects = tdict()
	h.obj_type = 'hexgrid'
	h.id = getId(h)
	rows = rows if rows % 2 != 0 else rows + 1  # bei hex muss das ungerade sein: was wenn nicht?
	h.topcols = cols  # cols in top row
	h.colarr = calc_hex_col_array(rows, h.topcols)
	h.maxcols = max(h.colarr)
	h.rows = rows
	h.cols = cols
	h.fields = []
	h.corners = []
	h.edges = []
	imiddleRow = (rows - 1) / 2
	indexRow = [-1, -1, 0, 0, 0, -1]
	indexCol = [0, 1, 1, 0, -1, -1]
	for irow in range(len(h.colarr)):
		colstart = h.maxcols - h.colarr[irow]
		for j in range(h.colarr[irow]):
			#field________________
			icol = colstart + 2 * j
			field = tdict()
			field.obj_type = 'field'
			field.id = getId(field)
			field.row = irow + 1
			field.col = icol + 1
			field.edges = [None] * 6
			field.fields = [None] * 6
			field.corners = [None] * 6
			h.objects[field.id] = field
			h.fields.append(field.id)

	#nodes________________
	for fid in h.fields:
		field = h.objects[fid]
		#nodes field is irow+1,icol+1
		for inode in range(6):
			#make node idByRC
			nrow = field.row + indexRow[inode]
			ncol = field.col + indexCol[inode]
			irc = 'n' + '-' + str(nrow) + '_' + str(ncol)
			node = None
			if irc in dhelp:
				node = dhelp[irc]
			else:
				node = tdict()
				node.obj_type = 'corner'
				node.id = getId(node)
				node.row = nrow
				node.col = ncol
				node.edges = [None, None, None]
				node.fields = [None, None, None]
				h.corners.append(node.id)
				dhelp[irc] = node
				h.objects[node.id] = node
			#fields of nodes ok
			if inode == 0:
				node.fields[1] = field.id
			elif inode == 1:
				node.fields[2] = field.id
			elif inode == 2:
				node.fields[2] = field.id
			elif inode == 3:
				node.fields[0] = field.id
			elif inode == 4:
				node.fields[0] = field.id
			elif inode == 5:
				node.fields[1] = field.id
			field.corners[inode] = node.id

	#edges________________
	for fid in h.fields:
		field = h.objects[fid]
		#field indices is irow+1,icol+1
		for inode in range(6):
			in1 = inode
			in2 = (inode + 1) % 6
			n1 = h.objects[field.corners[in1]]
			n2 = h.objects[field.corners[in2]]

			startNode = n1
			if n1.row > n2.row:
				startNode = n2
			if n1.row == n2.row and n1.col > n2.col:
				startNode = n2
			endNode = n2 if startNode == n1 else n1

			irc = 'e' + str(startNode.id) + '_' + str(endNode.id)
			edge = None
			if irc in dhelp:
				edge = dhelp[irc]
			else:
				edge = tdict()
				edge.obj_type = 'edge'
				edge.id = getId(edge)
				edge.row = startNode.row
				edge.col = startNode.col
				edge.fields = [None, None]
				edge.leftField = None
				edge.rightField = None
				edge.corners = [startNode.id, endNode.id]
				edge.startNode = startNode.id
				edge.endNode = endNode.id
				#add this edge id to each node's edges list ok
				if inode == 0:
					n1.edges[1] = edge.id
					n2.edges[2] = edge.id
				elif inode == 1:
					n1.edges[1] = edge.id
					n2.edges[0] = edge.id
				elif inode == 2:
					n1.edges[2] = edge.id
					n2.edges[0] = edge.id
				elif inode == 3:
					n1.edges[2] = edge.id
					n2.edges[1] = edge.id
				elif inode == 4:
					n1.edges[0] = edge.id
					n2.edges[1] = edge.id
				elif inode == 5:
					n1.edges[0] = edge.id
					n2.edges[2] = edge.id
				#add edge to board, dhelp
				h.edges.append(edge.id)
				dhelp[irc] = edge
				h.objects[edge.id] = edge
			if inode < 3:
				edge.fields[1] = field.id
				edge.leftField = field.id
			else:
				edge.fields[0] = field.id
				edge.rightField = field.id
			field.edges[inode] = edge.id

	#add fields of fields ok
	for fid in h.fields:
		f = h.objects[fid]
		for i in range(6):
			e = h.objects[f.edges[i]]
			for f1 in e.fields:
				if f1 and f1 != fid:
					f.fields[i] = f1
	return h