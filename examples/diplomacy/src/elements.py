
import sys, os
from itertools import chain
from omnibelt import load_yaml, save_yaml

import omnifig as fig

import pydip
from pydip.map import Map
from pydip.player import Player, command
from pydip.turn import resolve_turn, resolve_adjustment, resolve_retreats

from . import util

@fig.Component('map')
class DiploMap:
	def __init__(self, A):
		
		nodes_path = A.pull('nodes-path', None)
		edges_path = A.pull('edges-path', None)
		pos_path = A.pull('pos-path', None)
		
		name = A.pull('name', None)
		
		if nodes_path is None:
			nodes_path = 'nodes.yaml' if name is None else f'{name}_nodes.yaml'
		if edges_path is None:
			edges_path = 'edges.yaml' if name is None else f'{name}_edges.yaml'
		if pos_path is None:
			pos_path = 'pos.yaml' if name is None else f'{name}_pos.yaml'
		
		root = A.pull('root', None)
		if root is not None:
			nodes_path = os.path.join(root, nodes_path)
			edges_path = os.path.join(root, edges_path)
			pos_path = os.path.join(root, pos_path)
		
		self.nodes, self.edges = self._load_map_info(nodes_path, edges_path)
		self.get_ID_from_name = util.make_node_dictionary(self.nodes)
		
		self.pos = None if pos_path is None or not os.path.isfile(pos_path) else load_yaml(pos_path)
		
		self.dmap = self._create_dip_map(self.nodes, self.edges)
	
	def get_supply_centers(self):
		return [node for node in self.nodes if 'sc' in node]

	def _load_map_info(self, nodes_path, edges_path):
		
		nodes = load_yaml(nodes_path)
		
		coasts = util.separate_coasts(nodes)
		
		self.coasts = coasts
		
		# for node in nodes.values():
		# 	if 'coasts' in node:
		# 		del node['coasts']
		
		for ID, coast in coasts.items():
			origin = coast['coast-of']
			if 'coasts' not in nodes[origin]:
				nodes[origin]['coasts'] = []
			nodes[origin]['coasts'].append(ID)
		
		
		for ID, node in nodes.items():
			node['ID'] = ID
		
		edges = load_yaml(edges_path)
		
		return nodes, edges

	@staticmethod
	def _create_dip_map(nodes, edges):
		
		# descriptors
		
		descriptors = []
		
		for ID, node in nodes.items():
			desc = {'name': ID}
			if node['type'] != 'sea':
				desc['coasts'] = node.get('coasts', [])
			descriptors.append(desc)
			
		# adjacencies
		
		all_edges = util.list_edges(edges, nodes)
		adjacencies = set()

		for e in all_edges:
			
			start, end = e['start'], e['end']
			
			start = util.fix_loc(start, e['type'], nodes[start]['type']) if start in nodes else start
			end = util.fix_loc(end, e['type'], nodes[end]['type']) if end in nodes else end
			
			if (end, start) not in adjacencies:
				adjacencies.add((start, end))
			# adjacencies.add((start, end))

		adjacencies = list(adjacencies)
		
		
		return Map(descriptors, adjacencies)

	def _fix_loc(self, loc, utype):
		return util.fix_loc(loc, utype, self.nodes[loc]['type']) if loc in self.nodes else loc

	def _load_players(self, players):
		
		full = {}
		unit_info = {}
		
		for name, player in players.items():
			
			tiles = {loc: None for loc in player.get('control', [])}
			
			units = {unit['loc']: unit['type']
			              for unit in player.get('units', [])}
			
			for loc in units:
				if loc in self.coasts:
					cst = self.coasts[loc]['coast-of']
					if cst in tiles:
						del tiles[cst]
			
			tiles.update(units)
			
			unit_info.update({loc: (name, utype) for loc, utype in units.items()})
			
			config = [{'territory_name':self._fix_loc(loc, utype),
                        'unit_type': None if utype is None else util.UNIT_TYPES[utype],
		            } for loc, utype in tiles.items()]
			
			full[name] = Player(name=name, game_map=self.dmap,
		                    starting_configuration=config)
		
		units = {}
		for loc, (player, utype) in unit_info.items():
			fixed = self._fix_loc(loc, utype)
			unit = full[player].find_unit(fixed)
			units[loc] = unit
			units[fixed] = unit
		
		self.units = units
		self.players = full
		return self.players
	
	
	def process_actions(self, full):
		
		assert hasattr(self, 'players'), 'players have not been loaded'
		
		cmds = []
		
		for player, actions in full.items():
			
			player = self.players[player]
			
			for action in actions:
				unit = self.units[action['loc']]
				
				if action['type'] == 'move':
					action['dest'] = self._fix_loc(action['dest'], unit.unit_type)
					cmds.append(command.MoveCommand(player, unit, action['dest']))
				elif action['type'] == 'hold':
					cmds.append(command.HoldCommand(player, unit))
				elif 'support' in action['type']:
					sup_unit = self.units[action['dest' if 'defend' in action['type'] else 'src']]
					action['dest'] = self._fix_loc(action['dest'], sup_unit.unit_type)
					cmds.append(command.SupportCommand(player, unit, sup_unit, action['dest']))
				elif action['type'] == 'convoy-move':
					action['dest'] = self._fix_loc(action['dest'], unit.unit_type)
					cmds.append(command.ConvoyMoveCommand(player, unit, action['dest']))
				elif action['type'] == 'convoy-transport':
					transport = self.units[action['src']]
					action['dest'] = self._fix_loc(action['dest'], transport.unit_type)
					cmds.append(command.ConvoyTransportCommand(player, unit, transport, action['dest']))
				else:
					raise Exception(f'unknown: {action}')
		
		return cmds
		
	def process_retreats(self, full, retreats):
		
		assert hasattr(self, 'players'), 'players have not been loaded'
		
		cmds = []
		
		for player, actions in full.items():
			
			player = self.players[player]
			
			for action in actions:
				unit = self.units[action['loc']]
				
				if action['type'] == 'disband':
					cmds.append(command.RetreatDisbandCommand(retreats, player, unit))
				elif action['type'] == 'retreat':
					cmds.append(command.RetreatMoveCommand(retreats, player, unit, action['dest']))
				else:
					raise Exception(f'unknown: {action}')
		
		return cmds
	
	def process_builds(self, full, ownership):
		
		assert hasattr(self, 'players'), 'players have not been loaded'
		
		cmds = []
		
		for player, actions in full.items():
			
			player = self.players[player]
			
			for action in actions:
				unit = self.units[action['loc']]
				
				if action['type'] == 'build':
					cmds.append(command.AdjustmentCreateCommand(ownership, player, unit))
				elif action['type'] == 'destroy':
					cmds.append(command.AdjustmentDisbandCommand(player, unit))
				else:
					raise Exception(f'unknown: {action}')
		
		return cmds
		
	def _compute_retreat_map(self, retreats):
		
		rmap = {}
		
		raise NotImplementedError
		
	def _compute_ownership_map(self, players):
		
		raise NotImplementedError
		
	def uncoastify(self, loc, including_dirs=False):
		return self.coasts[loc]['coast-of'] if loc in self.coasts and \
			('dir' not in self.coasts[loc] or including_dirs) else loc
		
	def step(self, state, actions):
		
		self._load_players(state['players'])
		
		turn, season = state['time']['turn'], state['time']['season']
		retreat = 'retreat' in state['time']
		
		new = {'players':{player: {'units':[], 'control':[], 'centers':[]}
		                  for player, info in state['players'].items()}}
		
		
		players = new['players']

		retreats_needed = False
		adjustments_needed = False

		control = {}
		
		for name, info in players.items():
			old = state['players'][name]
			if 'name' in old:
				info['name'] = old['name']
			info['centers'] = old.get('centers', []).copy()
			for ctrl in old['control']:
				control[ctrl] = name
		
		if season < 3 and not retreat:
			actions = self.process_actions(actions)
			
			# resolve
			resolution = resolve_turn(self.dmap, actions)
			
			retreats = {}
			
			for player, units in resolution.items():
				for unit, sol in units.items():
					if sol is not None:
						retreats_needed = True
						raise NotImplementedError
						retreats[player] = sol
					
					players[player]['units'].append({'loc':self.uncoastify(unit.position),
					                                 'type': util.UNIT_ENUMS[unit.unit_type]})
					
					base = self.uncoastify(unit.position, True)
					if (season == 2 or 'sc' not in self.nodes[base] or self.nodes[base]['sc'] == 0) \
							and self.nodes[base]['type'] != 'sea':
						control[base] = player
			
			# check for retreats
			
			if season == 2:
				
				scores = {player: len(info.get('centers', [])) for player, info in state['players'].items()}
				
				# compute adjustments
				centers = {loc: player for loc, player in control.items()
				           if 'sc' in self.nodes[loc] and self.nodes[loc]['sc'] >= 1}
				
				for loc, player in centers.items():
					if loc not in players[player]['centers']:
						players[player]['centers'].append(loc)
			
				new['adjustments'] = {player: len(players[player]['centers']) - score
				                      for player, score in scores.items()}
				
				adjustments_needed = any(new['adjustments'].values())
			
			if len(retreats):
				raise NotImplementedError
				new['retreats'] = retreats
			
		elif retreat:
			
			retreat_map = self._compute_retreat_map(state['retreats'])
			
			actions = self.process_retreats(actions, retreat_map)
			
			# resolve retreats
			
		elif season == 3:
			actions = self.process_builds(actions)
			
			# adjustments
			
		else:
			raise Exception(f'unknown: {turn} {season} {retreat}')
		
		for loc, player in control.items():
			players[player]['control'].append(loc)
	
		# update time
		
		if retreats_needed:
			new['time'] = {'turn': turn, 'season': season, 'retreat': True}
			
		elif adjustments_needed:
			new['time'] = {'turn': turn, 'season': 3}
			
		elif season == 1:
			new['time'] = {'turn': turn, 'season': 2}
			
		else:
			new['time'] = {'turn': turn+1, 'season': 1}

		return new

# @fig.AutoComponent('state')
# class DiploState:
# 	def __init__(self, data=None, data_path=None):
# 		if data is None:
# 			assert data_path is not None, 'No data specified'
# 			data = load_yaml(data_path)
# 		if data is None:
# 			data = {}
		
		
		