

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
from git.examples.tictactoe_grid.main import TicTacToe

import numpy as np
from gsm import Array
x = Array(np.zeros(4))

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




