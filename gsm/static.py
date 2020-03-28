
import sys, os
import inspect
import ast

from graphviz import Digraph

from .errors import UnknownGameError
from .mixins import Named
from .io import registry



def get_ast(fn):
	#     print(fn)
	src = inspect.getsource(fn)
	lines = src.split('\n')
	while lines[0][0] == '\t':
		lines = [line[1:] for line in lines]
	if lines[0][0] == '@':
		lines = lines[1:]
	clean = '\n'.join(lines)
	m = ast.parse(clean)
	return m

def extract_info(r):
	typ = None
	name = None
	
	if isinstance(r, tuple):
		return r
	
	if typ is None:
		try:
			typ =  r.exc.func.id
		except AttributeError:
			pass
	if typ is None:
		try:
			typ = r.exc.func.attr
		except AttributeError:
			pass
	if typ is None:
		try:
			typ = r.exc.id
			name = 'none'
		except AttributeError:
			pass
	
	if typ is None:
		raise Exception()
		print('failed typ', ast.dump(r))
	
	if name is None:
		try:
			name = r.exc.args[0].s
		except AttributeError:
			pass
	
	if name is None and typ is not None:
		name = 'error'
	
	if name is None:
		raise Exception()
		print('failed name', ast.dump(r.exc))
	
	return typ, name

# def clean_info(r):
#     t, n = r

#     if n == 'error':
#         return False

#     if n == 'none':
#         return t in {'GameOver', 'PhaseComplete'}

#     if t in {'Switch', 'Decide', 'SwitchPhase', 'PhaseComplete', 'SubPhase'}:
#         return True

#     # allow for user defined signals (subclassing existing ones)

#     return False

class Collect_Raises(ast.NodeVisitor):
	def __init__(self, rs=None, cs=None, es=None):
		if rs is None:
			rs = []
		self.rs = rs
		if cs is None:
			cs = []
		self.cs = cs
		if es is None:
			es = []
		self.es = es
	def visit_Raise(self, node):
		self.rs.append(node)
	def visit_Call(self ,node):
		try:
			if node.func.value.id == 'self':
				name = node.func.attr
				
				if name == 'set_current_stage':
					self.es.append(node.args[0].s)
				else:
					
					self.cs.append(name)
		
		
		except Exception as e:
			#             raise e
			#             fc = node
			#             print('call failed')
			pass


def process_phase(phase, debug=False):
	def get_fn(name):
		nonlocal phase
		return getattr(phase, name, None)
	
	stages = phase._stage_registry
	
	calls = {}
	
	for name, fn in stages.items():
		
		calls[name] = process_fn(fn, get_fn=get_fn)
		if not debug:
			#             calls[name] = list(filter(clean_info, map(extract_info, calls[name])))
			calls[name] = list(map(extract_info, calls[name]))
			
			info = phase.get_stage_info(name)
			
			switch = info['switch']
			if switch is not None:
				calls[name].extend(('Switch', n) for n in switch)
			decide = info['decide']
			if decide is not None:
				calls[name].extend(('Decide', n) for n in decide)
			
	return calls


def process_fn(fn, raises=None, done=None, get_fn=None):
	calls = []
	if raises is None:
		raises = []
	if done is None:
		done = set()
	
	m = get_ast(fn)
	C = Collect_Raises(raises, calls)
	
	C.visit(m)
	
	for s in C.es:
		raises.append(('set_current', s))
	
	if get_fn is not None:
		#         print(f'Recursing on up to {len(calls)} function calls')
		for call in calls:
			fn = get_fn(call)
			if fn is not None and fn.__name__ not in done:
				done.add(fn.__name__)
				process_fn(fn, raises=raises, done=done)
	
	return raises


def connect_subs(all_sigs):
	# collect subs
	subs = {}
	for p, sigs in all_sigs.items():
		for s, rs in sigs.items():
			for t, n in rs:
				if t == 'SubPhase':
					if n not in subs:
						subs[n] = set()
					subs[n].add(p)
	
	# add trackers
	for p, sigs in all_sigs.items():
		if p in subs:
			for s, rs in sigs.items():
				for i in range(len(rs)):
					t, n = rs[i]
					if t == 'PhaseComplete':
						rs[i] = t, subs[p]
	
	return all_sigs


class Node(Named):
	#     fmt = {}
	def __init__(self, name, fmt=None):
		super().__init__(name)
		if fmt is None:
			fmt = {}
		self.fmt = fmt
	
	def get_format(self):
		fmts = []
		for cls in self.__class__.__mro__:
			try:
				fmts.append(cls.fmt)
			except AttributeError:
				pass
		fmts.append(self.fmt)
		
		fmt = {}
		for f in reversed(fmts):
			fmt.update(f)
		return fmt
	
	def __repr__(self):
		return '{}({})'.format(self.__class__.__name__, str(self.name))
	
	def __eq__(self, other):
		return repr(self) == repr(other)
	
	def __hash__(self):
		return id(self)
	
	def get_label(self):
		return self.name

class Edge(object):
	#     fmt = {}
	def __init__(self, A, B, fmt=None):
		self.A = A
		self.B = B
		if fmt is None:
			fmt = {}
		self.fmt = fmt
	
	def get_format(self):
		
		fmts = []
		for cls in self.__class__.__mro__:
			try:
				fmts.append(cls.fmt)
			except AttributeError:
				pass
		fmts.append(self.fmt)
		
		fmt = {}
		for f in reversed(fmts):
			fmt.update(f)
		return fmt
	
	def __str__(self):
		return '{} - {}'.format(self.A, self.B)
	
	def __repr__(self):
		return '{}({}, {})'.format(self.__class__.__name__, str(self.A), str(self.B))
	
	def __eq__(self, other):
		return repr(self) == repr(other)
	
	def __hash__(self):
		return id(self)
	
	def get_label(self):
		return str(self)

class StartNode(Node):
	fmt = {'shape': 'diamond', 'style': 'diagonals'}
	
	def __init__(self):
		super().__init__('Start Game')

class PhaseNode(Node):
	fmt = {'style': 'filled', 'color': 'purple'}
	
	def __init__(self, phase, **kwargs):
		self.phase = phase
		super().__init__(phase, **kwargs)
	
	def get_label(self):
		return 'begin'

class StageNode(Node):
	fmt = {'style': 'filled', 'color': 'skyblue'}
	
	def __init__(self, phase, stage, **kwargs):
		self.phase, self.stage = phase, stage
		super().__init__(f'{self.phase}.{self.stage}', **kwargs)
	
	def get_label(self):
		return '{}'.format(self.stage)

class DecisionNode(Node):
	fmt = {'shape': 'rect', 'style': 'rounded,filled', 'color': 'orange'}
	
	def __init__(self, phase, decision, **kwargs):
		self.phase, self.decision = phase, decision
		super().__init__(f'{self.phase}.{self.decision}', **kwargs)
	
	def get_label(self):
		return '{}'.format(self.decision)

class CompleteNode(Node):
	fmt = {'style': 'filled', 'color': 'limegreen'}
	
	def __init__(self, phase, **kwargs):
		self.phase = phase
		super().__init__(f'{self.phase} complete', **kwargs)
	
	def get_label(self):
		return 'complete'

class GameOverNode(Node):
	fmt = {'shape': 'rect', 'style': 'diagonals'}
	
	def __init__(self, **kwargs):
		super().__init__('Game Over', **kwargs)


class StartEdge(Edge):
	fmt = {}
	pass

class EntryEdge(Edge):
	fmt = {}
	pass

class CompleteEdge(Edge):
	fmt = {}
	pass

class GameOverEdge(Edge):
	fmt = {}
	pass

class SwitchEdge(Edge):
	fmt = {}
	pass

class SwitchPhaseEdge(Edge):
	fmt = {}
	pass

class SubPhaseEdge(Edge):
	fmt = {}
	pass

class SubPhaseBackEdge(Edge):
	fmt = {'style': 'dashed'}
	pass

class DecideEdge(Edge):
	fmt = {}
	pass

class DecideBackEdge(Edge):
	fmt = {'style': 'dotted'}
	pass


def analyze_game_flow(game):
	
	if game not in registry._game_registry:
		raise UnknownGameError(f'No game called {game} found. (Have you registerd it?)')
	
	info = registry._game_registry[game]
	
	phases = {n: v['cls'] for n, v in info['phases'].items()}

	node_types = [StartNode, PhaseNode, StageNode, DecisionNode, CompleteNode, GameOverNode]
	
	edge_types = [StartEdge, EntryEdge, CompleteEdge, GameOverEdge, SwitchEdge, SwitchPhaseEdge,
				  SubPhaseEdge, SubPhaseBackEdge, DecideEdge, DecideBackEdge]
	
	Rs = {}
	
	for name, phase in phases.items():
	
		Rs[name] = process_phase(phase)

	subbed = connect_subs(Rs)
	
	pnames = list(Rs.keys())
	snames = {name: list(phase._stage_registry.keys()) for name, phase in phases.items()}
	dnames = {name: list(phase._decision_registry.keys()) for name, phase in phases.items()}
	enames = {name: phase._entry_stage_name for name, phase in phases.items()}
	
	

	# nodes
	phase_nodes = {p:PhaseNode(p) for p in pnames}
	stage_nodes = {p:{s:StageNode(p, s) for s in stgs} for p, stgs in snames.items()}
	decision_nodes = {p:{d:DecisionNode(p, d) for d in decs} for p, decs in dnames.items()}
	complete_nodes = {p:CompleteNode(p) for p in pnames}
	game_over_node = GameOverNode()
	start_node = StartNode()


	# print([c.__name__ for c in node_types])
	# print([c.__name__ for c in edge_types])

	# edges
	
	entry_edges = [EntryEdge(phase_nodes[p], stage_nodes[p][s]) for p, s in enames.items()]

	E = []
	
	for p, sigs in subbed.items():
		for s, rs in sigs.items():
			try:
				origin = stage_nodes[p][s]
				for t, n in rs:
					if t == 'Switch':
						E.append(SwitchEdge(origin, stage_nodes[p][n]))
					elif t == 'set_current':
						entry_edges.append(EntryEdge(phase_nodes[p], stage_nodes[p][n]))
					elif t == 'Decide':
						E.append(DecideEdge(origin, decision_nodes[p][n]))
						E.append(DecideBackEdge(decision_nodes[p][n], origin))
					elif t == 'SwitchPhase':
						E.append(SwitchPhaseEdge(origin, complete_nodes[p]))
						E.append(SwitchPhaseEdge(complete_nodes[p], phase_nodes[n]))
					elif t == 'SubPhase':
						E.append(SubPhaseEdge(origin, phase_nodes[n]))
					elif t == 'PhaseComplete':
						E.append(CompleteEdge(origin, complete_nodes[p]))
						E.extend(SubPhaseBackEdge(complete_nodes[p], phase_nodes[g]) for g in n)
					elif t == 'GameOver':
						E.append(GameOverEdge(origin, game_over_node))
					else:
						print(f'skpped {t} {n}')
			except KeyError as k:
				print(p, s)
				raise k
	
	entry_nodes = {p: stage_nodes[p][s] for p, s in
				   enames.items()}  # TODO: check type of stage phase to see what nodes should be entry
	start_edge = StartEdge(start_node, phase_nodes[info['start_phase']])
	EDGES = entry_edges + E
	EDGES.append(start_edge)
	# EDGES = set(EDGES)
	
	
	NODES = []
	NODES.extend(phase_nodes.values())
	for stgs in stage_nodes.values():
		NODES.extend(stgs.values())
	for decs in decision_nodes.values():
		NODES.extend(decs.values())
	NODES.extend(complete_nodes.values())
	NODES.append(game_over_node)
	NODES.append(start_node)
	# NODES = set(NODES)
	
	
	edg = list({(repr(e.A),repr(e.B)):e for e in EDGES }.values())
	# nds = set(map(str, NODES))
	nds = NODES
	
	return nds, edg

	
def default_graph(game, name=None, directory='figures',
                  g=None, nodes=None, edges=None,
                  engine='dot', include_default_attrs=True,
                  **attrs):
	
	if name is None:
		name = f'{game}.gv'
	
	if g is None:
		g = Digraph('G', directory=directory, filename=name, engine=engine)
	
	if nodes is None or edges is None:
		nodes, edges = analyze_game_flow(game)
	
	info = registry._game_registry[game]
	pnames = list(info['phases'].keys())
	
	if include_default_attrs:
		if 'compound' not in attrs:
			attrs['compound'] = 'true'
		if 'newrank' not in attrs:
			attrs['newrank'] = 'true'
		if 'splines' not in attrs:
			attrs['splines'] = 'true'
		if 'concentrate' not in attrs:
			attrs['concentrate'] = 'true'
		if 'nodesep' not in attrs:
			attrs['nodesep'] = '0.4'
	
	# g.attr(compound='true')
	# g.attr(newrank='true')
	# g.attr(splines='true')
	#
	# # dot
	# g.attr(concentrate='true')
	# g.attr(nodesep='0.4')
	g.attr(**attrs)
	
	# neato
	# g.attr(model='circuit')
	# g.attr(mode='KK')
	# g.attr(overlap='prism')
	
	# fdp
	# g.attr(overlap='20:prism')
	# g.attr(nodesep='1.7')
	# g.attr(sep='0.1')
	
	# g.attr(smoothing='true')
	# g.attr(start='3')
	
	# g.attr(minlen='100')
	# g.attr(sep='1')
	# g.attr(repulsiveforce='1.0')
	# g.attr(pin='true')
	
	for p in pnames:
		
		with g.subgraph(name='cluster_{}'.format(p)) as s:
			s.attr(label=p)
			for n in nodes:
				#             if isinstance(n, PhaseNode):
				#                 pass
				#             elif isinstance(n, CompleteNode):
				#                 pass
				if hasattr(n, 'phase') and n.phase == p:
					s.node(repr(n), label=n.get_label(), **n.get_format())
	
	#         for e in edg:
	#             a,b = e.A, e.B
	#             if hasattr(a, 'phase') and a.phase == p \
	#             and hasattr(b, 'phase') and b.phase == p:
	#                 s.edge(e.A.get_label(), e.B.get_label(), **e.get_format())
	
	# for e in edg:
	#     a,b = e.A, e.B
	#     if not hasattr(a, 'phase') or not hasattr(b, 'phase') or a.phase != b.phase:
	#         g.edge(e.A.get_label(), e.B.get_label(), **e.get_format())
	
	# with g.subgraph(name='starts') as s:
	#     s.attr(rank='same')
	#     for n in phase_nodes.values():
	#         s.node(repr(n), label=n.get_label(), **n.get_format())
	
	# with g.subgraph(name='ends') as s:
	#     s.attr(rank='same')
	#     for n in complete_nodes.values():
	#         s.node(repr(n), label=n.get_label(), **n.get_format())
	
	# with g.subgraph(name='ctrl') as s:
	#     s.attr(rank='same')
	#     n = game_over_node
	#     s.node(repr(n), label=n.get_label(), **n.get_format())
	#     n = start_node
	#     s.node(repr(n), label=n.get_label(), **n.get_format())
	
	for n in nodes:
		if not hasattr(n, 'phase'):
			g.node(repr(n), label=n.get_label(), **n.get_format())
	
	for e in edges:
		
		fmt = e.get_format()
		
		a, b = e.A, e.B
		
		#     if isinstance(a, (PhaseNode):
		#         fmt['lhead'] = f'cluster_{a.phase}'
		
		if hasattr(a, 'phase') and hasattr(b, 'phase') and a.phase == b.phase:
			pass
		else:
			#         if isinstance(a, CompleteNode):
			#             fmt['ltail'] = f'cluster_{a.phase}'
			
			#         if isinstance(b, PhaseNode):
			#             fmt['lhead'] = f'cluster_{b.phase}'
			pass
		
		#     if isinstance(e, DecideBackEdge):
		#         continue
		
		g.edge(repr(a), repr(b), **fmt)
	
	# for n in nds:
	#     g.node(n.get_label(), **n.get_format())
	# for e in edg:
	#     g.edge(e.A.get_label(), e.B.get_label(), **e.get_format())
	
	# g.view()
	return g
