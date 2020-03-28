
import sys, os

import gsm
import examples

from gsm.static import default_graph


def make_graph(game, **kwargs):

	print('Building graph for {}'.format(game))
	g = default_graph(game, **kwargs)
	g.view()
	



if __name__ == '__main__':
	
	argv = sys.argv
	
	if sys.gettrace() is not None:
		argv = ['', 'aristocracy']
	
	game = argv[1]
	
	make_graph(game)
	


