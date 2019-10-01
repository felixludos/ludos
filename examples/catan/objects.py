from gsm import GameObject
from gsm.mixins import Named
from gsm.common.world import grid
from gsm.common.elements import Card

class Board(grid.Grid):
	pass

class Hex(grid.Field):
	pass


class DevCard(Named, Card):
	pass




