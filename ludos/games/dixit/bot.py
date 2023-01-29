
import discord
from omnibelt import unspecified_argument
import omnifig as fig
from pathlib import Path
from PIL import Image

from ...interfaces.discord import DiscordBot, as_command, as_event


_DEFAULT_ROOT = str(Path(__file__).parents[0])

@fig.component('dixit-bot')
class DixitBot(DiscordBot):
	def __init__(self, root=_DEFAULT_ROOT, **kwargs):
		super().__init__(**kwargs)
		self._root = Path(root) / 'data'
		self._load_data(self._root)
		self._tmproot = self._root / 'tmp'
		self._tmproot.mkdir(exist_ok=True)

		self.visions = {}
		self.votes = {}

	def _load_data(self, root):
		self._imgroot = root / 'cards'
		
		self._visioncards = list(self._imgroot.glob('img*'))
		# self._visioncards = list(self._imgroot.glob('vision*'))
		# self._visioncards = list(self._imgroot.glob('character*'))
		
	
	@as_event
	async def on_reaction_remove(self, reaction, user):
		if user in self.votes and reaction == self.votes[user]:
			del self.votes[user]
		if user in self.visions and reaction == self.visions[user]:
			del self.visions[user]
	
	async def _start_game(self, ctx, *args):
		# num = len(self.players)
		
		self._num_hand_cards = 6
		# self._max_score = 20
		
		self._rng.shuffle(self.players)
		self._rng.shuffle(self._visioncards)
		self._discardpile = []
		
		self.story_idx = 0
		self.storyteller = None
		
		self.score = {player: 0 for player in self.players}
		
		self.hands = {player: [] for player in self.players}
		self._round_counter = 0
		await self._start_round()
		
		
	def _get_imgpath(self, i, g='img'):
		return self._imgroot / f'{g}{i}.png'
		
		
	def _load_concat_imgs(self, *imgpaths):
		images = [Image.open(path) for path in imgpaths]
		
		scaled = []
		for image in images:
			w, h = image.size
			h = 300 / w * h
			# img = image
			img = image.resize((300, int(h)), Image.ANTIALIAS)
			img = img.crop((0, 0, 300, 450))
			# img = image.resize((int(w*scale), int(h*scale)), Image.ANTIALIAS)
			scaled.append(img)
		images = scaled
		
		if len(images) == 1:
			return images[0]
		
		widths, heights = zip(*(i.size for i in images))
		total_width = sum(widths)
		max_height = max(heights)
		
		new_im = Image.new('RGB', (total_width, max_height))
		
		x_offset = 0
		for im in images:
			new_im.paste(im, (x_offset, 0))
			x_offset += im.size[0]
		return new_im
		
	def _get_tmp_img_path(self, img, ident=None):
		if ident is None:
			ident= '0'
		path = self._tmproot / f'{ident}.jpg'
		img.save(path)
		return path
		
	def _draw_vision_card(self, N=1):
		if N > len(self._visioncards):
			self._visioncards = self._discardpile.copy()
			self._rng.shuffle(self._visioncards)
		
		return [self._visioncards.pop() for _ in range(N)]
		
	async def _start_round(self):
		self._round_counter += 1
		self.storyteller = self.players[self.story_idx % len(self.players)]
		self.story_idx += 1
		
		await self.table.send(f'**Round {self._round_counter}!** {self.storyteller.display_name} is the storyteller now.')
		
		for player, hand in self.hands.items():
			if len(hand) < self._num_hand_cards:
				hand.extend(self._draw_vision_card(self._num_hand_cards - len(hand)))
			
			handpath = self._get_tmp_img_path(self._load_concat_imgs(*hand), ident=str(player).replace('#', '-'))
			await self.interfaces[player].send('These are your cards', file=discord.File(str(handpath)))
		
		await self.interfaces[self.storyteller].send(f'{self.storyteller.mention} Tell a story about one of your cards')
		await self.register_message_query(self.interfaces[self.storyteller], self.storyteller, self._story_pick)
		self._status = f'Waiting for {self.storyteller.display_name} tell the story.'


	async def _story_pick(self, message):
		self.story = message.clean_content
		await self.table.send(f'The story prompt is:\n\n*{self.story}*\n')
		await self._prompt_visions()
		return True
		
		
	async def _prompt_visions(self):
		
		self.visions = {}
		
		for player, hand in self.hands.items():
			msg = await self.interfaces[player].send(f'{player.mention} Select the card that best matches the story:\n\n*{self.story}*\n')
			nums = self._number_emojis[1:len(hand)+1]
			await self.register_reaction_query(msg, self._pick_vision, *nums)

		self._status = 'Waiting for everyone to submit their story cards'
		# self._status = 'Waiting for {} to submit their story cards'.format(', '.join(
		# 	p.display_name for p in self.players if p not in self.visions))
		

	async def _pick_vision(self, reaction, user):
		if user in self.visions:
			old = self.visions[user]
			del self.visions[user]
			await old.remove(user)
		self.visions[user] = reaction

		missing = [p.display_name for p in self.players if p not in self.visions]
		if len(missing):
			self._status = 'Waiting for {} to submit their story cards'.format(', '.join(missing))
		else:
			self._reaction_queries.clear()
			await self._resolve_visions()
			return 'done'

	async def _resolve_visions(self):
		
		picked = {}
		
		for player, rct in self.visions.items():
			i = self._number_emojis.index(rct.emoji)-1
			picked[player] = self.hands[player][i]
			self._discardpile.append(self.hands[player][i])
			del self.hands[player][i]
		
		self.visions.clear()
		self.picked = picked
		self.order = list(picked.keys())
		self._rng.shuffle(self.order)
		
		nums = self._number_emojis[1:len(picked) + 1]
		
		visions = [self.picked[p] for p in self.order]
		visionpath = self._get_tmp_img_path(self._load_concat_imgs(*visions), ident='table')
		await self.table.send('These are the selected cards', file=discord.File(str(visionpath)))
		# msg = await self.table.send(f'{self.guild.default_role}: Vote on the card that best matches the story')
		
		self.votes = {}
		for player in self.players:
			if player != self.storyteller:
				comm = self.interfaces[player]
				txt = f'{player.mention} Vote on the card that best matches the story'
				msg = await comm.send(txt, file=discord.File(str(visionpath)))
				await self.register_reaction_query(msg, self._vote, *nums)
		self._status = 'Waiting for everyone to submit their vote'


	async def _vote(self, reaction, user):
		if user in self.votes:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)
		self.votes[user] = reaction

		missing = [p.display_name for p in self.players if p not in self.votes and p != self.storyteller]
		if len(missing):
			self._status = 'Waiting for {} to submit their vote'.format(', '.join(missing))
		else:
			self._reaction_queries.clear()
			await self._resolve_vote()
			return 'done'
	
	
	async def _resolve_vote(self):
		
		picks = {}
		
		for player, rct in self.votes.items():
			i = self._number_emojis.index(rct.emoji) - 1
			picks[player] = self.order[i]
		self.votes.clear()
		
		correct = [player for player, pick in picks.items() if player != self.storyteller and pick == self.storyteller]
		wrong = [player for player, pick in picks.items() if player != self.storyteller and pick != self.storyteller]
		
		lines = []
		
		lines.append(f'The correct card was: {self._number_emojis[self.order.index(self.storyteller)+1]}')
		
		if len(correct) and len(wrong):
			# good story
			lines.append(f'**Good story!** {len(correct)} players picked the correct card.')
			for player in sorted(self.players, key=lambda p: (p in correct, p in wrong, str(p)), reverse=True):
				if player == self.storyteller:
					self.score[player] += 3
				if player in correct:
					lines.append(f'**{player.display_name}** got the *correct* card **(+3)**')
					self.score[player] += 3
				if player in wrong and player != picks[player]:
					self.score[picks[player]] += 1
					lines.append(f'**{player.display_name}** picked **{picks[player].display_name}** **(+1)**')
					# lines.append(f'**{picks[player].display_name}** was picked by **{player.display_name}** **(+1)**')
			pass
		else:
			# bad story
			if len(correct):
				lines.append(f'**Bad story!** All players picked the correct card.')
			else:
				lines.append(f'**Bad story!** No players picked the correct card.')
			for player in self.players:
				if player != self.storyteller:
					self.score[player] += 2
		
		lines.append('\n__Score__')
		lines.extend(f'{player.display_name}: **{score}**'
		             for player, score in sorted(self.score.items(), reverse=True,
		                                         key=lambda item: (item[1],item[0].display_name)))
		
		await self.table.send('\n'.join(lines))
		
		await self._start_round()
		
		
		

