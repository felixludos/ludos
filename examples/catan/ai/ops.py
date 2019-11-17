
import gsm
from gsm import tdict, tlist, tset

def compute_missing(resources, costs):
	dists = tdict()
	missing_res = tdict()
	for building, cost in costs.items():
		dists[building] = 0
		missing = tdict()
		for res, num in cost.items():
			if num > resources[res]:
				diff = num - resources[res]
				dists[building] += diff
				missing[res] = diff
		missing_res[building] = missing
	return missing_res, dists




