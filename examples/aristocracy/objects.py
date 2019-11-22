from gsm import GameObject
from gsm.mixins import Named
from gsm.common.world import grid
from gsm.common.elements import Card as CardBase
from gsm.common.elements import Deck

class Card(Named, CardBase):
	pass

class DiscardPile(Deck):
	pass

class DrawPile(Deck):
	pass





