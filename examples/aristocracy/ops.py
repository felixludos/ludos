
from gsm import tset, tlist, tdict
from gsm.common.world import grid

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






