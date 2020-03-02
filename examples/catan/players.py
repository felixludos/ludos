from gsm import GamePlayer
from gsm.mixins import Named
from gsm.common.world import grid
from gsm.common.elements import Card, Deck

class CatanPlayer(GamePlayer, game='catan', open={'num_res', 'color', 'devcards', 'buildings',
		                                'reserve', 'ports', 'past_devcards'}):
	pass



