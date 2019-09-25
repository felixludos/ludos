

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

I.select_action()
I.step()
I.set_player()
I.get_status()
I.view()

