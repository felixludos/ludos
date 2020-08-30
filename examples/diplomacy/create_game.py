
import sys, os

import omnifig as fig

from src import util

@fig.Script('new-diplo', description='Create a new Diplomacy game')
def create_diplo_game(A):
	
	M = A.pull('map')
	
	print(M)
	
	return M


if __name__ == '__main__':
	fig.entry('new-diplo')
	
