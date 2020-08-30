
from ludos import gdict, glist, gset

def count_vp(buildings, values):
	vps = 0
	for type, owned in buildings.items():
		vps += values[type] * len(owned)
	return vps

def compute_missing(resources, costs):
	dists = gdict()
	missing_res = gdict()
	for building, cost in costs.items():
		dists[building] = 0
		missing = gdict()
		for res, num in cost.items():
			if num > resources[res]:
				diff = num - resources[res]
				dists[building] += diff
				missing[res] = diff
		missing_res[building] = missing
	return missing_res, dists




