
import sys, os
from itertools import chain
from omnibelt import load_yaml, save_yaml

import omnifig as fig

import pydip


@fig.AutoScript('render', description='Take a Diplomacy step')
def diplomacy_step(map, players, state=None, state_path=None):
	pass


if __name__ == '__main__':
	fig.entry('render')
