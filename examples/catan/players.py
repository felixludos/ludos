from ludos import GamePlayer
from ludos.mixins import Named
from ludos.common.world import grid
from ludos.common.elements import Card, Deck

class CatanPlayer(GamePlayer, game='catan', open={'num_res', 'color', 'devcards', 'buildings',
		                                'reserve', 'ports', 'past_devcards'}):
	pass



