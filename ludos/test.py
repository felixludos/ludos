
from omnibelt import unpack
import omnifig as fig

import gsm
from gsm import dummy

@fig.Script('test-dummy')
def _test_dummy(A):
	
	T = gsm.GameTable()
	
	T.get_available_games()
	T.set_game('dummy')
	
	T.add_player('p1')
	T.add_player('p2')
	
	T.start_game()
	
	raw = T.get_status('p1')
	status = unpack(raw)
	

	print('LOG:')
	print(status.log)
	print()

	print('ACTIONS:')
	print(status.actions)
	print()

	print('STATUS:')
	print(status)
	
	return 0
	
	