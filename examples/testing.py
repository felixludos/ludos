

import sys, os, time
from collections import namedtuple, OrderedDict
import random
from string import Formatter
from itertools import chain, product
import json
import gsm
from gsm import tdict, tlist, tset
from gsm import util
from gsm import viz
from gsm.viz import Ipython_Interface as Interface
import yaml

from gsm.viz import Ipython_Interface as Interface
from catan.main import Catan

seed = 1
I = Interface(Catan(), seed=seed, full_log=True)
I.set_player('White')

# I.reset(seed=seed)
# I.view()
I.load('saves/catan_setup.pkl')

I.set_player()
I.get_status()

for i in range(10):
	I.select_action(0)
	I.step()
	I.set_player()
	I.get_status()
	I.view()
	print('\n\n\n')



if False:
	
	test_yaml = '../../test_yaml.yaml'
	data = viz.unjsonify(yaml.load(open(test_yaml,'r')))
	M = data['map']
	M = 'A'
	print('\n'.join(M))
	
	info = grid_util._create_grid(M, grid_type='hex',
	              wrap_rows=False, wrap_cols=False,
	#               enforce_connectivity=True,
	              enable_edges=True, enable_corners=True, enable_boundary=False,
	                )
	
	print(info.keys())
	print(info.map)

if False:
	seed = 1
	
	I = Interface(TicTacToe(), seed=seed)
	
	I.set_player('Player1')
	
	I.reset(seed=seed)
	I.view()
	
	I.select_action()
	I.step()
	I.set_player()
	I.get_status()
	I.view()
	
	out = I.save()
	print(out)
	
	J = Interface(TicTacToe(), seed=seed)
	J.load(out)
	
	print('J loaded')
	
	J.select_action()
	J.step()
	J.set_player()
	J.get_status()
	J.view()
	
	print()
	print('I')
	print()
	
	I.select_action()
	I.step()
	I.set_player()
	I.get_status()
	I.view()
	
	
	
	
