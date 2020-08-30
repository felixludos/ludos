
from ludos import gset, glist, gdict
from ludos.common.world import grid

def satisfies_vic_req(player, reqs):
	
	for req in reqs:
		works = True
		for bld, num in req.items():
			if len(player.buildings[bld]) < num:
				works = False
				break
		if works:
			return True
		else:
			continue
	
	return False


def get_next_market(selected):
	
	mn = None
	nxt = None
	
	for player, cards in selected.items():
		if len(cards):
			val = sum([card.val for card in cards]) + player.order / 10
			
			if mn is None or val < mn:
				mn = val
				nxt = player
	
	return nxt
	



