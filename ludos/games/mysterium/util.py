import random
import math
from pathlib import Path
from PIL import Image

class Deck:
	def __init__(self, cards, rng=None, auto_discard=False):
		if rng is None:
			rng = random.Random()
		self._rng = rng
		
		self.deck = cards.copy()
		self.discards = []
		self._rng.shuffle(self.deck)
		self._auto_discard = auto_discard
		
		
	def reset(self):
		self.deck = [*self.discards, *self.deck]
		self._rng.shuffle(self.deck)
		
	
	def draw(self, N=1):
		if len(self.deck) < N:
			self._rng.shuffle(self.discards)
			self.deck = [*self.discards, *self.deck]
			self.discards.clear()
		cards = [self.deck.pop() for _ in range(N)]
		if self._auto_discard:
			self.discard(*cards)
		return cards
		
		
	def discard(self, *cards):
		self.discards.extend(cards)
		


def factors(n):  # has duplicates, starts from the extremes and ends with the middle
	return (x for tup in ([i, n // i]
	                      for i in range(1, int(n ** 0.5) + 1) if n % i == 0) for x in tup)


def tile_elements(*elms, H=None, W=None, prefer_tall=False):
	H, W = calc_tiling(len(elms), H=H, W=W, prefer_tall=prefer_tall)
	# assert H*W == len(elms), f'{len(elms)} vs {H} * {W}'
	itr = iter(elms)
	return [[next(itr ,None) for _ in range(W)] for _ in range(H)]


def calc_tiling(N, H=None, W=None, prefer_tall=False):
	
	if H is not None and W is None:
		W = int(math.ceil(N / H))
	if W is not None and H is None:
		H = int(math.ceil(N / W))
	
	if H is not None and W is not None and N == H * W:
		return H, W
	
	H, W = tuple(factors(N))[-2:]  # most middle 2 factors
	
	if H > W or prefer_tall:
		H, W = W, H
	
	# if not prefer_tall:
	# 	H,W = W,H
	return H, W


def get_tmp_img_path(img, root, ident='0'):
	path = root / f'{ident}.png'
	img.save(path)
	return path
	

def load_concat_imgs(*imgpaths, H=None, W=None, scale=None, prefer_tall=False):
	images = [Image.open(path) for path in imgpaths]
	
	if scale is not None:
		scaled = []
		for image in images:
			w, h = image.size
			img = image.resize((int(w * scale), int(h * scale)), Image.ANTIALIAS)
			scaled.append(img)
		images = scaled
	
	if len(images) == 1:
		return images[0]
	
	tiles = tile_elements(*images, H=H, W=W, prefer_tall=prefer_tall)
	
	H, W = len(tiles), len(tiles[0])
	widths, heights = zip(*(i.size for i in images))
	mW, mH = max(widths), max(heights)
	
	new_im = Image.new('RGB', (W * mW, H * mH))
	for i, row in enumerate(tiles):
		for j, im in enumerate(row):
			if im is not None:
				new_im.paste(im, (j * mW, i * mH))
	
	thW, thH = 4000, 3000
	w, h = new_im.size
	if h > thH:
		scale = thH / h
		new_im = new_im.resize((int(w * scale), int(h * scale)), Image.ANTIALIAS)
	w, h = new_im.size
	if w > thW:
		scale = thW / w
		new_im = new_im.resize((int(w * scale), int(h * scale)), Image.ANTIALIAS)
	return new_im

