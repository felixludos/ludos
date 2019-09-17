import traceback
import json
from git.gsm.signals import PhaseComplete
# from .structures import tdict, tset, tlist




def add_next_phase(G, phase):
	G.game.sequence.insert(G.game.index + 1, phase)

def switch_phase(G, phase):
	G.game.sequence.insert(G.game.index, phase)


def create_gamestate():
	
	G = tdict()
	
	game = tdict()
	game.sequence = tlist()
	game.index = 0
	
	G.game = game
	
	
	
	return G
	
	



