import discord
from omnibelt import unspecified_argument
import omnifig as fig
import math
from pathlib import Path
from PIL import Image

from ...interfaces.discord import DiscordBot, as_command, as_event, as_loop
from .util import tile_elements, get_tmp_img_path, load_concat_imgs

_DEFAULT_ROOT = str(Path(__file__).parents[0])


@fig.Component('mysterium-bot')
class MysteriumBot(DiscordBot):
	def __init__(self, A, root=unspecified_argument, **kwargs):
		if root is unspecified_argument:
			root = A.pull('root', _DEFAULT_ROOT)
		super().__init__(A, **kwargs)
		self._root = Path(root) / 'data'
		self._load_data(self._root)
		self._tmproot = self._root / 'tmp'
		self._tmproot.mkdir(exist_ok=True)

		self.vision = None
		self.det_msgs = None
		self.ready = set()
		self.det_votes = {}
		self.truth = None
	
	def _load_data(self, root):
		self._imgroot = root / 'assets'
		
		self._visioncards = list((self._imgroot/'vision').glob('*'))
		self._rng.shuffle(self._visioncards)
		self._discardpile = []
		
		caselbls = ['person', 'location', 'object', 'story']
		self._casecards = {lbl: list((self._imgroot/lbl).glob('*')) for lbl in caselbls}
		for deck in self._casecards.values():
			self._rng.shuffle(deck)
		
	
	def _draw_vision_card(self, N=1):
		if N > len(self._visioncards):
			self._visioncards = self._discardpile.copy()
			self._rng.shuffle(self._visioncards)
		
		return [self._visioncards.pop() for _ in range(N)]
	
	@as_command('start')
	async def on_start(self, ctx, ghostname=None):
		if self._insufficient_permissions(ctx.author):
			await ctx.send(f'{ctx.author.display_name} does not have sufficient permissions for this.')
			return
		
		gameroom = discord.utils.get(self.guild.channels, name='GameRoom')
		if gameroom is not None:
			for channel in gameroom.channels:
				await channel.delete()
			await gameroom.delete()
		self.gameroom = await self.guild.create_category_channel('GameRoom')
		
		# _players = ['bobmax', 'felixludos', 'Lauren', 'GooseOnTheLoose']
		player_role = discord.utils.get(self.guild.roles, name='Player')
		# _players = []
		# _members = {member.display_name: member for member in self.get_all_members()}
		# self._players = [_members[player] for player in _players]
		self.players = [player for player in player_role.members if not player.bot]
		for player in self.players:
			await self._setup_player(player)
			

		self.ghost = discord.utils.get(self.players, display_name=ghostname)
		self.detectives = [p for p in self.players if p != self.ghost]
		
		self.table = await self._create_channel('table', *self.detectives, remove_existing=True, private=True)
		
		self._status = ''
		await self._start_game(ctx)
	
	async def _start_game(self, ctx):
		self.case_seq = ['person', 'location', 'object']
		# self.case_seq = ['person', 'location', 'story']
		# self.case_seq = ['person']
		
		self._ghost_hand_size = 7
		self._time_in_minutes = 5

		self._det_supports_reset_round = 4
		self._max_rounds = 7
		self.ravens = 3
		self._det_supports = 3
		
		self.round = 0

		distractors = None
		if distractors is None:
			distractors = {1:3, 2: 4, 3: 3, 4: 4,
			              5: 4, 6: 4, 7: 3,
			              8: 4, 9: 3, 10: 5}[len(self.detectives)]
		
		await self.table.send(f'There are {len(self.detectives)} detectives and {self.ghost.display_name} is the ghost')
		
		self.cases = {det: {
			lbl: self._casecards[lbl].pop() for lbl in self.case_seq
		} for det in self.detectives}
		
		self.progress = {det: 0 for det in self.detectives}
		self.score = {det: 0 for det in self.detectives}
		self.support_guesses = {det: self._det_supports for det in self.detectives}
		
		self.leads = {lbl: [self._casecards[lbl].pop() for _ in range(distractors)]
		                   + [self.cases[det][lbl] for det in self.detectives]
		              for lbl in self.case_seq}
		for cards in self.leads.values():
			self._rng.shuffle(cards)

		self.hand = self._draw_vision_card(self._ghost_hand_size)
		await self.interfaces[self.ghost].send(f'You have {self.ravens} raven/s to replace all your vision cards.')
		
		solpath = get_tmp_img_path(load_concat_imgs(
			*[self.cases[det][lbl] for det in self.detectives for lbl in self.case_seq],
			W=max(1,len(self.case_seq))), self._tmproot, ident='sol')
		await self.interfaces[self.ghost].send('\n'.join(
			['__Solutions__ (top secret)', *[det.display_name for det in self.detectives]]
		), file=discord.File(str(solpath)))

		# await self._show_leads(self.case_seq[0]) # TESTING

		await self._prep_ghost_round()


	async def _end_game(self, votes=None, truth=None, round=None, win=False):
		self.detective_timer.cancel()
		self.final_timer.cancel()
		self._reaction_queries.clear()
		self._message_queries.clear()
		
		if round is not None:
			det_msg = 'Game Over! The detectives didn\'t identify the suspects fast enough - everyone loses.'
			ghost_msg = det_msg
		elif votes is not None:
			true_emoji = self._number_emojis[truth+1]
			correct = []
			picks = {}
			for det, reaction in votes.items():
				if reaction.emoji not in picks:
					picks[reaction.emoji] = 0
				picks[reaction.emoji] += 1
				if reaction.emoji == true_emoji:
					correct.append(det)
			
			count = len(correct)
			if count > len(self.detectives)//2:
				det_msg = 'Game Over! The case was solved - everyone wins!'
				ghost_msg = det_msg
			else:
				best = max(picks.values())
				selected = ', '.join([k for k, v in picks.items() if v == best])
				det_msg = f'Game Over! The true case was {true_emoji} - everyone loses.'
				ghost_msg = f'Game Over! The wrong case was chosen ({selected}) - everyone loses.'
		else:
			msg = 'Game Over! The case was solved - everyone wins!' if win else 'Game Over!'
			det_msg = msg
			ghost_msg = msg
		
		await self.table.send(det_msg)
		await self.interfaces[self.ghost].send(ghost_msg)
		
	
	async def _prep_ghost_round(self):
		self.round += 1
		if self.round > self._max_rounds:
			await self._end_game(round=self.round)
			return

		round_msg = f'__**Round {self.round}!**__ The ghost will now select the visions for ' \
		            f'the remaining {len(self.progress)} detectives.'
		if self.round == self._max_rounds:
			round_msg += '\n**LAST ROUND!** You must get all remaining cases correct.'
		await self.interfaces[self.ghost].send(round_msg)
		await self.table.send(round_msg)
		if self.round == self._det_supports_reset_round:
			await self.table.send(f'All detectives have {self._det_supports} supports again.')
			self.support_guesses.update({det: self._det_supports for det in self.support_guesses})
		
		self.visions = {}
		
		await self._ghost_round()
	
	_raven_icon = '🃏'
	
	async def _ghost_round(self):
		
		if len(self.hand) < self._ghost_hand_size:
			self.hand.extend(self._draw_vision_card(self._ghost_hand_size - len(self.hand)))
		
		missing = [det for det in self.detectives if det not in self.visions and det in self.progress]
		if not len(missing):
			await self._prep_detective_round()
			return
		
		self._status = f'Waiting for ghost to select hints for {len(missing)} player/s'
		
		self.current_det = missing[0]
		
		await self._ghost_prompt(show_sol=True)

	
	async def _ghost_prompt(self, show_sol=False):
		
		det = self.current_det
		self.vision = set()
		comm = self.interfaces[self.ghost]
		
		if show_sol:
			if det in self.progress:
				sol = self.cases[det][self.case_seq[self.progress[det]]]
				promptpath = get_tmp_img_path(load_concat_imgs(sol, H=1), self._tmproot, ident='ghost')
				msg = f'{det.display_name} needs to find'
			else:
				sols = [self.cases[det][c] for c in self.case_seq]
				promptpath = get_tmp_img_path(load_concat_imgs(*sols, H=1), self._tmproot, ident='ghost')
				msg = f'The correct case (from {det.display_name}) is'
			await comm.send(msg, file=discord.File(str(promptpath)))
		
		rec = f'{det.display_name}' if det in self.progress else 'everyone'
		
		handpath = get_tmp_img_path(load_concat_imgs(*self.hand, H=1), self._tmproot, ident='ghost')
		msg = await comm.send(f'{self.ghost.mention} Select the hint for {rec}',
		                      file=discord.File(str(handpath)))
		
		nums = self._number_emojis[1:len(self.hand) + 1]
		options = nums.copy()
		if self.ravens:
			options.append(self._raven_icon)
		options.append(self._accept_mark)
		
		await self.register_reaction_query(msg, self._update_ghost_vision, *options)
	
	
	@as_event
	async def on_reaction_remove(self, reaction, user):
		if user == self.ghost and self.vision is not None and reaction.emoji in self.vision:
			self.vision.remove(reaction.emoji)
		if user != self.ghost and self.det_msgs is not None and reaction.message in self.det_msgs \
			and self.det_msgs[reaction.message] not in self.ready \
			and user in self.det_votes[self.det_msgs[reaction.message]]\
				and self.det_votes[self.det_msgs[reaction.message]] == reaction:
			del self.det_votes[self.det_msgs[reaction.message]][user]
		if self.truth is not None and user in self.votes and user not in self.ready:
			del self.votes[user]
	
	
	async def _update_ghost_vision(self, reaction, user):
		if reaction.emoji == self._raven_icon:
			self.ravens -= 1
			await self.table.send('A raven crows.')
			self._discardpile.extend(self.hand)
			self.hand.clear()
			self.hand.extend(self._draw_vision_card(self._ghost_hand_size))
			await self.interfaces[self.ghost].send(f'The raven replaces all your vision cards '
			                                       f'(you have {self.ravens} raven/s remaining)')
			
			await self._ghost_prompt()
			return 'done'
		
		if reaction.emoji == self._accept_mark:
			
			inds = [self._number_emojis.index(i)-1 for i in self.vision]
			self._rng.shuffle(inds)
			
			vision = [self.hand[i] for i in inds]
			self._discardpile.extend(vision)
			for v in vision:
				self.hand.remove(v)
			
			if self.current_det in self.progress:
				self.visions[self.current_det] = vision
				await self._ghost_round()
			else:
				self.vision = vision
				await self._final_detective_round()
			return 'done'
		
		self.vision.add(reaction.emoji)
	
	
	async def _show_leads(self, cat):
		
		lines = [f'__{cat.capitalize()} options__']
		
		elms = self.leads[cat]
		
		nums = self._number_emojis[1:len(elms)+1]
		
		tbl = tile_elements(*nums)
		
		for row in tbl:
			lines.append(' '.join(r for r in row if r is not None))
		
		catpath = get_tmp_img_path(load_concat_imgs(*elms, H=len(tbl)), self._tmproot, ident='cat')
		await self.table.send('\n'.join(lines), file=discord.File(str(catpath)))
	
		return nums
		
	
	async def _prep_detective_round(self):
		
		await self.table.send('The ghost has prepared all the visions')
		
		self.det_msgs = {}
		self.ready = set()
		self.det_votes = {}
		
		nums = None
		prev = -1
		for det, vision in sorted(self.visions.items(), key=lambda item: (self.progress[item[0]],
                                                              self.detectives.index(item[0]))):
			ind = self.progress[det]
			cat = self.case_seq[ind]
			if ind != prev:
				nums = await self._show_leads(cat)
			prev = ind
			
			comm = self.interfaces[det]
			if len(vision):
				visionpath = get_tmp_img_path(load_concat_imgs(*vision, H=1), self._tmproot, ident='cat')
				await comm.send(f'Round {self.round} vision for *{cat.capitalize()}*',
				                file=discord.File(str(visionpath)))
			else:
				await comm.send(f'Round {self.round} vision for *{cat.capitalize()}*\n**__NO VISION__**')
			
			msg = await self.table.send(f'Vote on **{det.display_name}**\'s case')
			self.det_msgs[msg] = det
			self.det_votes[det] = {}
			await self.register_reaction_query(msg, self._detective_pick, *nums, self._accept_mark)
		
		self._status = f'Waiting for {len(self.detectives)} detectives to vote on their cases.'
		self.detective_timer.cancel()
		self.detective_timer.start()
		
	
	async def _detective_pick(self, reaction, user):
		
		if user not in self.detectives:
			return
		
		det = self.det_msgs[reaction.message]
		if det in self.ready and det == user:
			return
		
		if det == user and reaction.emoji == self._accept_mark:
			self.ready.add(det)
			self._status = f'Waiting for {len(self.detectives)-len(self.ready)} detectives to vote on their cases.'
			if len(self.ready) == len(self.det_msgs):
				self._reaction_queries.clear()
				await self._resolve_detectives()
				return 'done'
			return
		
		if user in self.det_votes[det]:
			old = self.det_votes[det][user]
			del self.det_votes[det][user]
			await old.remove(user)
		self.det_votes[det][user] = reaction
	
	
	@as_loop(minutes=1)
	async def detective_timer(self):
		if self.detective_timer.current_loop == self._time_in_minutes:
			await self.table.send(f'{self.guild.default_role}: **Time is up!**')
			self.detective_timer.stop()
			await self._resolve_detectives(True)
		elif self.detective_timer.current_loop == 0:
			await self.table.send(f'{self.guild.default_role}: You have {self._time_in_minutes} '
			                      f'minutes to vote for your case and support another detective\'s.')
		elif self._time_in_minutes - self.detective_timer.current_loop == 1:
			await self.table.send(f'{self.guild.default_role}: **1 minute remaining!**')
		else:
			await self.table.send(f'**{self._time_in_minutes - self.detective_timer.current_loop}** minutes remaining!')


	async def _resolve_detectives(self, times_up=False):
		if not times_up:
			self.detective_timer.cancel()
		self._reaction_queries.clear()
		
		def _extract_vote(cat, reaction):
			if reaction.emoji in self._number_emojis:
				index = self._number_emojis.index(reaction.emoji) - 1
				return self.leads[cat][index]
		
		cats = {det: self.case_seq[self.progress[det]] for det in self.det_votes}
		picks = {det: _extract_vote(cats[det], votes[det]) for det, votes in self.det_votes.items() if det in votes}
		
		supports = {}
		for det, votes in self.det_votes.items():
			sups = {}
			for sup, vote in votes.items():
				if sup != det and self.support_guesses[sup] and det in picks:
					sups[sup] = _extract_vote(cats[det], vote) == picks.get(det)
					self.support_guesses[sup] -= 1
			supports[det] = sups
		
		lines = []
		for det, pick in picks.items():
			cat = cats[det]
			correct_img = self.cases[det][cat]
			correct = pick == correct_img
			supporters = [s for s, v in supports.get(det, {}).items() if v == correct]

			if correct:
				self.progress[det] += 1
				self.leads[cat].remove(correct_img)
				
			if self.progress[det] >= len(self.case_seq):
				del self.progress[det]
			
			pass_msg = 'found the correct' if correct else 'picked the wrong'
			sup_msg = ''
			if len(supporters):
				sups = ', '.join([s.display_name for s in supporters])
				sup_msg = f' (predicted by: {sups})'
			
			lines.append(f'**{det.display_name}** {pass_msg} *{cat.capitalize()}*{sup_msg}')
			
			for sup in supporters:
				self.score[sup] += 1
		
		lines.append('__Clairvoyance__')
		for det, score in sorted(self.score.items(), reverse=True, key=lambda x: (x[1], x[0].display_name)):
			lines.append(f'{det.display_name}: **{score}** ({self.support_guesses[det]} support/s remaining)')
		
		await self.table.send('\n'.join(lines))
		
		if len(self.progress):
			await self._prep_ghost_round()
		else:
			await self._prep_final_round()
			
			
	async def _prep_final_round(self):
		
		msg = f'All cases have been compiled, now the true case must be identified.'
		await self.table.send(msg)
		await self.interfaces[self.ghost].send(msg)
		
		if len(self.hand) < self._ghost_hand_size:
			self.hand.extend(self._draw_vision_card(self._ghost_hand_size - len(self.hand)))
		
		self.current_det = self._rng.choice(self.detectives)
		self.truth = self.detectives.index(self.current_det)
		await self._ghost_prompt(show_sol=True)
		
		
	async def _final_detective_round(self):
		if len(self.detectives) == 1:
			await self._end_game(win=True)
		else:
			solpath = get_tmp_img_path(load_concat_imgs(
				*[self.cases[det][lbl] for det in self.detectives for lbl in self.case_seq],
				W=max(1,len(self.case_seq))), self._tmproot, ident='sol')
		
			nums = self._number_emojis[1:len(self.detectives)+1]
			await self.table.send('\n'.join(['__Cases__', *nums]), file=discord.File(str(solpath)))
			
			visionpath = get_tmp_img_path(load_concat_imgs(*self.vision, H=1), self._tmproot, ident='final')
			await self.table.send(f'Vision for the final round', file=discord.File(str(visionpath)))
			
			self.votes = {}
			self.ready = set()
			msg = await self.table.send(f'Vote on the **final** case')
			await self.register_reaction_query(msg, self._final_detective_pick, *nums, self._accept_mark)
			
			self.final_timer.start()
		

	@as_loop(minutes=1)
	async def final_timer(self):
		if self.final_timer.current_loop == self._time_in_minutes:
			await self.table.send(f'{self.guild.default_role}: **Time is up!**')
			self.final_timer.stop()
			await self._end_game(votes=self.votes, truth=self.truth)
		elif self.final_timer.current_loop == 0:
			await self.table.send(f'{self.guild.default_role}: You have {self._time_in_minutes} '
			                      f'minutes to vote for the final case.')
		elif self._time_in_minutes - self.final_timer.current_loop == 1:
			await self.table.send(f'{self.guild.default_role}: **1 minute remaining!**')
		else:
			await self.table.send(f'**{self._time_in_minutes - self.final_timer.current_loop}** minutes remaining!')

		
	async def _final_detective_pick(self, reaction, user):
		if user not in self.detectives:
			return
		if user in self.ready:
			return
		
		if reaction.emoji == self._accept_mark:
			self.ready.add(user)
			if len(self.ready) == len(self.detectives):
				await self._end_game(votes=self.votes, truth=self.truth)
		
		if user in self.votes:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)
		self.votes[user] = reaction
		
		
		
