from gsm import GameObject
from gsm.mixins import Named
from gsm.common.world import grid
from gsm.common.elements import Card

class Board(grid.Grid, game='catan'):
	pass

class Hex(grid.Field, game='catan'):
	pass

class DevCard(Named, Card, game='catan'):
	pass




