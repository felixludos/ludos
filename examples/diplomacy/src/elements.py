
import sys, os
from itertools import chain
from omnibelt import load_yaml, save_yaml

import omnifig as fig

import pydip
from pydip.map import Map

from . import util

@fig.AutoComponent('map')
class DiploMap:
	def __init__(self, nodes_path, edges_path, pos_path=None):
		
		self.nodes, self.edges = self._load_map_info(nodes_path, edges_path)
		
		self.pos = None if pos_path is None else load_yaml(pos_path)
		
		self._dmap = self._create_dip_map(self.nodes, self.edges)

	@staticmethod
	def _load_map_info(nodes_path, edges_path):
		
		nodes = load_yaml(nodes_path)
		
		coasts = util.separate_coasts(nodes)
		
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
		
		descriptors = [{'name': ID,
		                'coasts': node.get('coasts', [])}
		               for ID, node in nodes.items()]
		
		# adjacencies
		
		all_edges = util.list_edges(edges)
		adjacencies = set()

		for e in all_edges:
			start, end = e['start'], e['end']
			
			if e['type'] == 'army' and (end, start) not in adjacencies:
				adjacencies.add((start, end))

			elif e['type'] == 'navy':
				if start in nodes and 'coasts' in nodes[start]:
					start = nodes[start]['coasts'][0]
				elif end in nodes and 'coasts' in nodes[end]:
					end = nodes[end]['coasts'][0]
				
				if (end, start) not in adjacencies:
					adjacencies.add((start, end))
				

		adjacencies = list(adjacencies)
		
		
		return Map(descriptors, adjacencies)

