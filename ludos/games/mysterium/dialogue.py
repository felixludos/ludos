import random

import discord
from omnibelt import unspecified_argument
import omnifig as fig
from tqdm import tqdm
import math
from pathlib import Path
from PIL import Image

from ...interfaces.discord import DiscordBot, as_command, as_event, as_loop
from .util import Deck, tile_elements, calc_tiling, get_tmp_img_path, load_concat_imgs

_DEFAULT_ROOT = str(Path(__file__).parents[0])


@fig.Component('mysticdialogue-bot')
class MysticDialogueBot(DiscordBot):
	def __init__(self, A, root=unspecified_argument, **kwargs):
		if root is unspecified_argument:
			root = A.pull('root', _DEFAULT_ROOT)
		super().__init__(A, **kwargs)
		self._root = Path(root) / 'data'
		self._load_data(self._root)
		self.tmproot = self._root / 'tmp'
		self.tmproot.mkdir(exist_ok=True)
		
	
	def _load_data(self, root):
		self._imgroot = root / 'assets'
		
		self.visioncards = list((self._imgroot / 'vision').glob('*'))
		self._rng.shuffle(self.visioncards)
		
		caselbls = ['person', 'location', 'object', 'story']
		self.casecards = {lbl: list((self._imgroot / lbl).glob('*')) for lbl in caselbls}
		for deck in self.casecards.values():
			self._rng.shuffle(deck)
	
	
	# @as_command('start')
	# async def on_start(self, ctx):
	# 	if self._insufficient_permissions(ctx.author):
	# 		await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
	# 		return
	#
	# 	gameroom = discord.utils.get(self.guild.channels, name='GameRoom')
	# 	if gameroom is not None:
	# 		for channel in gameroom.channels:
	# 			await channel.delete()
	# 		await gameroom.delete()
	# 	self.gameroom = await self.guild.create_category_channel('GameRoom')
	#
	# 	# _players = ['bobmax', 'felixludos', 'Lauren', 'GooseOnTheLoose']
	# 	player_role = discord.utils.get(self.guild.roles, name='Player')
	# 	# _players = []
	# 	# _members = {member.display_name: member for member in self.get_all_members()}
	# 	# self._players = [_members[player] for player in _players]
	# 	self.players = [player for player in player_role.members if not player.bot]
	# 	for player in self.players:
	# 		await self._setup_player(player)
	#
	# 	self.table = await self._create_channel('table', *self.players, remove_existing=True, private=True)
	#
	# 	self._status = ''
	# 	await self._start_game(ctx)

	async def _setup_player(self, member):
		pass
	
	async def _start_game(self, ctx):
		self.components = ['person', 'location']
		
		self._num_ghosts = {}
		self._num_mystics = {}
		self._default_num_ghosts = 1
		self._default_num_mystics = 1

		self._mystics_distractors = {}
		self._ghost_distractors = {}
		self._default_mystic_distractors = 5
		self._default_ghost_distractors = 3
		self._max_hand_size = 7

		self._default_mystic_distractors = 10
		self._default_ghost_distractors = 8
		self._max_hand_size = 12
		
		
		players = [player.display_name for player in self.players]
		# assert len()
		self._rng.shuffle(players)
		
		gcount = [self._num_ghosts.get(player, self._default_num_ghosts) for player in players]
		mcount = [self._num_mystics.get(player, self._default_num_mystics) for player in players]
		assert sum(gcount) == sum(mcount), f'Counts dont match: {len(gcount)} vs {len(mcount)}'
		
		players = [discord.utils.get(self.players, display_name=name) for name in players]
		
		ghost_options = {player: self._num_ghosts.get(player.display_name, self._default_num_ghosts)
		                 for player, num in zip(players, gcount) if num > 0}
		pairs = {}
		for mystic in players:
			ghosts = []
			for _ in range(self._num_mystics.get(mystic.display_name, self._default_num_mystics)):
				options = [(num, ghost not in ghosts, ghost)
				           for ghost, num in ghost_options.items() if ghost != mystic]
				assert len(options)
				_, _, ghost = next(iter(sorted(options, reverse=True)))
				ghosts.append(ghost)
				ghost_options[ghost] -= 1
				if ghost_options[ghost] == 0:
					del ghost_options[ghost]
			pairs[mystic] = ghosts

		cases = []
		for mystic, ghosts in pairs.items():
			for i, ghost in enumerate(ghosts):
				mystic_channel = await self._create_channel(f'mystic-{mystic.display_name}-{i+1}', mystic, private=True)
				ghost_channel = await self._create_channel(f'ghost-{ghost.display_name}-{i+1}', ghost, private=True)
				
				cases.append( self.DialogueCase(self, mystic_channel, ghost_channel, mystic, ghost,
				                                mystic_distractors=self._mystics_distractors.get(
					                                mystic.display_name, self._default_mystic_distractors),
				                                ghost_distractors=self._ghost_distractors.get(
					                                ghost.display_name, self._default_ghost_distractors),
				                                hand_size=self._max_hand_size, seed=self._rng.getrandbits(32),
				                                mystic_component=self.components[0],
				                                ghost_component=self.components[1]) )
		
		self.cases = cases
		
		self.results = {player: [] for player in players}
		
		for case in tqdm(cases, desc='Opening Cases'):
			await case.open_case()

		for case in tqdm(cases, desc='Starting Cases'):
			await case.start_case()


	async def score_case(self, case, picked):
		score = picked == case.solution, case.cost, case
		self.results[case.mystic.player].append(score)
		self.results[case.ghost.player].append(score)
		
		await case.open_case()
		await case.start_case()
		msg = 'A mystic has successfully solved a case.' if score[0] else 'A mystic has failed to solve a case.'
		await self.table.send(msg)
		
	
	@as_command('score')
	async def get_score(self, ctx):
		if ctx.author in self.results:
			cost = sum(v for s, v, _ in self.results[ctx.author] if s)
			count = len([1 for s, v, _ in self.results[ctx.author] if s])
			total = len(self.results[ctx.author])
			
			av = f' (with an average of {sum(cost)/count:1.1f} messages)' if count>0 else ''
			await ctx.send(f'You have succeeded {count}/{total}{av}')
			

	
	class DialogueCase:
		def __init__(self, game, mystic_channel, ghost_channel, mystic, ghost,
		             mystic_distractors=5, ghost_distractors=3,
		             mystic_component='person', ghost_component='location',
		             hand_size=7, seed=None):
			self._rng = random.Random(seed)
			self.game = game
			self.case_num = 0
			self.vision_msg = None
			
			self.mystic = self.PlayerInfo('mystic', mystic_channel, mystic, mystic_component, mystic_distractors+1,
			                              hand_size, self.game, self._rng)
			self.ghost = self.PlayerInfo('ghost', ghost_channel, ghost, ghost_component, ghost_distractors+1,
			                              hand_size, self.game, self._rng)
			
			limit = max(self.mystic.num, self.ghost.num)
			self.mystic.vocab = self._rng.sample(self.game.casecards[self.mystic.component], k=limit)
			self.ghost.vocab = self._rng.sample(self.game.casecards[self.ghost.component], k=limit)
			
			
		class PlayerInfo:
			def __init__(self, role, channel, player, component, num, hand_size,
			             game, rng=None):
				self._rng = rng
				self.role = role
				self.channel = channel
				self.player = player
				self.component = component
				self.num = num
				
				self.game = game
				self.deck = Deck(self.game.visioncards, auto_discard=True, rng=rng)
				self.hand = []
				self.vocab = None
				self.options = None
				
				self._max_hand_size = hand_size
		
			def reset(self):
				self.deck.reset()
				self.hand.clear()
				
			def fill_hand(self):
				self.hand.extend(self.deck.draw(self._max_hand_size - len(self.hand)))
		
		
		async def open_case(self):
			self.case_num += 1
			await self.mystic.channel.send(f'__**Starting case {self.case_num}**__')
			await self.ghost.channel.send(f'__**Starting case {self.case_num}**__')
			
			self.cost = 0
			self.ghost.reset()
			self.mystic.reset()
			
			num = max(self.mystic.num, self.ghost.num)
			mystic_options = self._rng.sample(self.ghost.vocab, num)
			self.ghost.pairs = list(zip(self._rng.sample(self.mystic.vocab, self.ghost.num), mystic_options))
			self.mystic.options = mystic_options[:self.mystic.num]
			
			self.mystic.prompt, self.solution = self.ghost.pairs[0]
			self._rng.shuffle(self.mystic.options)
			self._rng.shuffle(self.ghost.pairs)
			
			promptpath = get_tmp_img_path(load_concat_imgs(self.mystic.prompt), self.game.tmproot, ident='prompt')
			await self.mystic.channel.send(f'Use your mystical powers to communicate this *{self.mystic.component}* '
			                               f'to the spirits.', file=discord.File(str(promptpath)))
			
			pairspath = get_tmp_img_path(load_concat_imgs(*[im for pair in self.ghost.pairs for im in pair], W=2),
			                             self.game.tmproot, ident='pair')
			await self.ghost.channel.send(f'From the great beyond you know all and see all. Use the visions of the '
			                               f'mystic to identify the correct {self.mystic.component}, and guide '
			                               f'the mystic to find the corresponding *{self.ghost.component}*',
			                               file=discord.File(str(pairspath)))
			
			optpath = get_tmp_img_path(load_concat_imgs(*self.mystic.options, H=1), self.game.tmproot, ident='options')
			msg = await self.mystic.channel.send(f'The spirits will guide you towards the correct '
			                                     f'*{self.ghost.component}*, given the {self.mystic.component} above. '
				                               f'Once you are confident you know the correct *{self.ghost.component}*, '
				                               f'select the corresponding number here.',
				                               file=discord.File(str(optpath)))
			
			self.sol_msg = msg
			await self.game.register_reaction_query(msg, self._select_solution,
			                                  *self.game._number_emojis[1:len(self.mystic.options)+1])
			
			await self.ghost.channel.send('Waiting for the mystic to present the first hint.')
			
			
		async def _select_solution(self, reaction, user):
			if user == self.mystic.player and reaction.emoji in self.game._number_emojis:
				await self.end_case()
				picked = self.mystic.options[self.game._number_emojis.index(reaction.emoji)-1]
				
				if picked == self.solution:
					await self.mystic.channel.send(f'You have identified the **correct** {self.ghost.component}. '
					                               f'You score 1 point (after transmitting {self.cost} visions)')
					await self.ghost.channel.send(f'The mystic has divined the **correct** {self.ghost.component} '
					                              f'from your visions. You score 1 point (after '
					                              f'{self.cost} transmissions)')
				
				else:
					
					solpath = get_tmp_img_path(load_concat_imgs(self.solution), self.game.tmproot, ident='solution')
					await self.mystic.channel.send(f'You chose the **wrong** {self.ghost.component}, the correct one was',
					                               file=discord.File(str(solpath)))
					solpath = get_tmp_img_path(load_concat_imgs(self.mystic.prompt, picked), self.game.tmproot,
					                           ident='solution')
					await self.ghost.channel.send(f'The mystic has chosen the **wrong** {self.ghost.component}. '
					                              f'Here is the correct {self.mystic.component} followed '
					                              f'by the {self.ghost.component} that the mystic selected.',
					                               file=discord.File(str(solpath)))
				
				await self.game.score_case(self, picked)
				return 'done'
		
		
		async def end_case(self):
			if self.vision_msg in self.game._reaction_queries:
				del self.game._reaction_queries[self.vision_msg]
			if self.sol_msg in self.game._reaction_queries:
				del self.game._reaction_queries[self.sol_msg]
				
			
		async def start_case(self):
			self.active, self.passive = self.mystic, self.ghost
			await self._prompt_vision()
		
		
		async def _prompt_vision(self):
			self.active.fill_hand()
			
			handpath = get_tmp_img_path(load_concat_imgs(*self.active.hand, H=1), self.game.tmproot, ident='hand')
			msg = await self.active.channel.send(f'{self.active.player.mention} Select what cards to send to '
			                                     f'the {self.passive.role}', file=discord.File(str(handpath)))
			
			self.vision_msg = msg
			self.selection = set()
			await self.game.register_reaction_query(msg, self._pick_vision,
			                    *self.game._number_emojis[1:len(self.active.hand)+1], self.game._accept_mark,
			                                  remove_callback=self._remove_vision)
			
		
		async def _pick_vision(self, reaction, user):
			if user == self.active.player:
				if reaction.emoji == self.game._accept_mark:
					await self.send_vision()
					return 'done'
				elif reaction.emoji in self.game._number_emojis:
					self.selection.add(reaction)
		

		async def _remove_vision(self, reaction, user):
			if user == self.active.player:
				self.selection.discard(reaction)
		
		
		async def send_vision(self):
			vision = [self.active.hand[self.game._number_emojis.index(reaction.emoji)-1]
			          for reaction in self.selection]
			cost = max(1, len(vision))
			
			for card in vision:
				self.active.hand.remove(card)
			self._rng.shuffle(vision)
			
			if len(vision):
				visionpath = get_tmp_img_path(load_concat_imgs(*vision, H=1), self.game.tmproot, ident='vision')
				await self.passive.channel.send(f'The {self.active.role} has offers this vision to identify '
				                                f'the *{self.active.component}*', file=discord.File(str(visionpath)))
			else:
				await self.passive.channel.send(f'**The {self.active.role} remains silent.**')
			
			await self.active.channel.send(f'You have sent your {len(vision)} card vision to the {self.passive.role}.')
			self.cost += cost
			
			self.active, self.passive = self.passive, self.active
			await self._prompt_vision()



