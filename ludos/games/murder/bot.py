
import discord
import omnifig as fig

from ...interfaces.discord import DiscordBot, as_command, as_event



@fig.Component('murder-bot')
class MurderBot(DiscordBot):
	
	@as_event
	async def on_reaction_remove(self, reaction, user):
		if user in self.votes and reaction == self.votes[user]:
			del self.votes[user]
		if reaction in self._resolution_picks:
			self._resolution_picks.remove(reaction)
	
	# Murder
	
	_board_rewards = {
		# 2: [None, 'membership', 'draw', 'pick', 'kill'], # TESTING
		
		5: [None, None, 'draw', 'kill', 'kill'],
		6: [None, None, 'draw', 'kill', 'kill'],
		
		7: [None, 'membership', 'pick', 'kill', 'kill'],
		8: [None, 'membership', 'pick', 'kill', 'kill'],
		
		9: ['membership', 'membership', 'pick', 'kill', 'kill'],
		10: ['membership', 'membership', 'pick', 'kill', 'kill'],
	}
	
	_notify_murderer = True
	_secret_votes = False
	
	_accept_mark = '✅'  # '✔️'
	_reject_mark = '❎'  # '❌'
	
	_vote_yes = '👍'
	_vote_no = '👎'
	
	_number_emojis = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
	
	async def _start_game(self):
		num = len(self.players)
		if num not in self._board_rewards:
			await self.table.send(f'Wrong number of players: {num}')
			return
		
		self._bonus_rewards = self._board_rewards[num]
		
		acc = (num + 1) // 2 - 2
		# acc = 1 # TESTING
		# await self.table.send('[Using testing setup - forced one accomplice]')
		roles = ['a cop'] * (num - acc - 1) + ['an accomplice'] * acc + ['the murderer']
		self._rng.shuffle(roles)
		for player, role in zip(self.players, roles):
			self._roles[player] = role
		
		murderer = [player for player in self.players if self._roles[player] == 'the murderer'][0]
		accomplices = [player for player in self.players if self._roles[player] == 'an accomplice']
		
		await self.table.send('Player order: {}'.format(', '.join(p.display_name for p in self.players)))
		msg = await self.table.send(f'There are {acc} accomplice/s and 1 murderer.')
		# await msg.add_reaction(self._accept_mark)
		# await msg.add_reaction(self._reject_mark)
		
		await self.table.send('The executive actions are: {}'.format(', '.join(
			('' if reward is None else reward) for reward in self._bonus_rewards)))
		
		for player in self.players:
			role = self._roles[player]
			crim = 'blue' if 'cop' in role else 'red'
			await self.interfaces[player].send(f'You are {role} ({crim}).')
			if role == 'an accomplice':
				await self.interfaces[player].send(f'The murderer is {murderer.display_name}.')
			if role == 'an accomplice' or (role == 'the murderer' and self._notify_murderer):
				await self.interfaces[player].send('The accomplices are {}.'
				                                   .format(', '.join(a.display_name for a in accomplices)))
		
		self.commissioner, self.detective = None, None
		self.candidates = []
		self._past_higherups = []
		
		self._deck = ['red'] * 11 + ['blue'] * 6
		self._rng.shuffle(self._deck)
		self._discard_pile = []
		self._passed_resolutions = {'red': 0, 'blue': 0}
		self._resolution_picks = set()
		self._rejected_candidates = 0
		self._pre_special_commissioner = None
		self._special_commissioner = None
		self._investigated = set()
		
		# await self.table.send('Test mode: 5 red policies have already been passed')
		# self._passed_resolutions['red'] = 5
		
		await self._start_new_round()
	
	
	async def _start_new_round(self):
		
		prev = None
		if self.commissioner is not None:
			self._past_higherups = self.commissioner, self.detective
			prev = self.commissioner
		
		if self._pre_special_commissioner is not None:
			prev = self._pre_special_commissioner
			self._pre_special_commissioner = None
		
		if prev is None and len(self.candidates):
			prev = self.candidates[0]
		
		self.commissioner, self.detective = None, None
		
		if self._special_commissioner is None:
			if prev is None:
				candidate = self._rng.choice(self.players)
			else:
				idx = self.players.index(prev)
				candidate = self.players[(idx + 1) % len(self.players)]
		else:
			candidate = self._special_commissioner
			self._pre_special_commissioner = prev
		self._special_commissioner = None
		
		self.candidates.clear()
		self.candidates.append(candidate)
		
		await self.table.send(f'{candidate.display_name} is the police commissioner candidate.')
		
		comm = self.interfaces[candidate]
		await comm.send(f'{candidate.mention}: Select the next candidate detective (type their name here).')
		
		self._detective_options = {player for player in self.players
		                           if player != candidate and player not in self._past_higherups}
		await comm.send('Options: {}'.format(', '.join(p.display_name for p in self._detective_options)))
		
		# self._queries[comm, candidate] = self.
		await self.register_message_query(comm, candidate, self._pick_detective)
		self._status = f'Waiting for {candidate.display_name} to select the next detective candidate.'
	
	
	async def _check_reshuffle_deck(self):
		if len(self._deck) < 3:
			self._deck.extend(self._discard_pile)
			self._rng.shuffle(self._deck)
			self._discard_pile.clear()
			await self.table.send(f'The deck of resolutions has been reshuffled ({len(self._deck)} cards).')
	
	
	# reactions = message.reactions
	# return reactions
	
	
	async def _pick_detective(self, message):
		
		# if not len(message.mentions):
		# 	await message.channel.send('You haven\'t mentioned anyone, write "@" followed by a player name')
		
		pick = discord.utils.get(self.players, display_name=message.clean_content)
		# pick = message.mentions[0]
		
		if pick not in self._detective_options:
			await message.channel.send('Invalid input, you should mention one of these players: {}'
			                           .format(', '.join(p.mention for p in self._detective_options)))
			return
		
		self.candidates.append(pick)
		
		await self._prep_vote()
	
	# 	msg = await message.channel.send(f'Confirm you picked {pick.display_name} as the detective candidate.')
	# 	await self._reaction_query(msg, self._set_detective, self._accept_mark, self._reject_mark)
	# 	return pick
	#
	#
	# async def _set_detective(self, reaction, user):
	#
	# 	if reaction.emoji == self._accept_mark:
	# 		await self._prep_vote()
	# 		return
	#
	# 	comm = reaction.message.channel
	# 	await comm.send('Select the next candidate detective (type their name here).')
	# 	await comm.send('Options: {}'.format(', '.join(p.display_name for p in self._detective_options)))
	# 	return reaction
	
	
	async def _prep_vote(self):
		await self.table.send('The candidates for police commissioner and detective are ready:')
		await self.table.send(f'**Police commissioner: {self.candidates[0].display_name}**')
		await self.table.send(f'**Detective: {self.candidates[1].display_name}**')
		msg = await self.table.send(f'{self.guild.default_role}: Vote for these candidates now.')
		await self.register_reaction_query(msg, self._count_vote, self._vote_yes, self._vote_no)
		
		self.votes = {}
		self._status = 'Waiting for {} to vote on the candidates'.format(
			', '.join(p.display_name for p in self.players if p not in self.votes))
	
	
	async def _count_vote(self, reaction, user):
		if user in self.votes:
			old = self.votes[user]
			del self.votes[user]
			await old.remove(user)
		self.votes[user] = reaction
		
		missing = [p.display_name for p in self.players if p not in self.votes]
		if len(missing):
			self._status = 'Waiting for {} to vote on the candidates'.format(', '.join(missing))
		else:
			self._reaction_queries.clear()
			await self._resolve_vote()
			return 'done'
	
	
	async def _resolve_vote(self):
		
		cnt = sum((1 if v.emoji == self._vote_yes else -1) for v in self.votes.values())
		
		if cnt > 0:
			await self.table.send('Congratulations! The candidates are accepted.')
			self.commissioner, self.detective = self.candidates[:2]
			self._rejected_candidates = 0
			
			if self._passed_resolutions['red'] >= 3 and self._roles[self.detective] == 'the murderer':
				await self.table.send('Since at least three red resolutions have been passed and '
				                      'the murderer has been elected to be the detective, the criminals win!')
				await self._end_game('criminals')
				return
			
			await self._3_resolutions()
		else:
			await self.table.send('The vote is complete, but the candidates are rejected.')
			self._rejected_candidates += 1
			if self._rejected_candidates == 3:
				card = self._deck.pop()
				await self._check_reshuffle_deck()
				
				await self.table.send(f'Due to three failed votes, the next resolution is enacted '
				                      f'automatically, which is **{card}**.')
				self._passed_resolutions[card] += 1
				await self._check_victory(card)
				self._rejected_candidates = 0
			
			await self._start_new_round()
		
		self.votes.clear()
	
	
	async def _check_victory(self, passed):
		
		await self.table.send('Overall {} blue and {} red resolution/s have been passed.'
		                      .format(self._passed_resolutions['blue'], self._passed_resolutions['red']))
		
		if self._passed_resolutions['blue'] == 5:
			await self._end_game('cops')
		if self._passed_resolutions['red'] == 6:
			await self._end_game('criminals')
	
	
	async def _3_resolutions(self):
		await self.table.send(f'The commissioner {self.commissioner.display_name} '
		                      f'must select two out of the three possible resolutions')
		
		nums = self._number_emojis[1:4]
		self._resolution_options = {num: self._deck.pop() for num in nums}
		
		for num, option in self._resolution_options.items():
			await self.interfaces[self.commissioner].send(f'{num}: {option}')
		msg = await self.interfaces[self.commissioner].send(f'{self.commissioner.mention}: '
		                                                     f'Specify which **2** resolutions to **keep** '
		                                                     'by selecting the corresponding number.')
		self._resolution_picks = set()
		await self.register_reaction_query(msg, self._picked_2_resolutions, *nums)
		self._status = f'Waiting for {self.commissioner.display_name} to select 2 resolutions'
	
	
	
	
	async def _picked_2_resolutions(self, reaction, user):
		self._resolution_picks.add(reaction)
		
		if len(self._resolution_picks) == 2:
			picks = {r.emoji for r in self._resolution_picks}
			discard = [e for e in self._resolution_options if e not in picks]
			assert len(discard) == 1
			discard = discard[0]
			self._discard_pile.append(self._resolution_options[discard])
			
			nums = self._number_emojis[1:3]
			self._resolution_options = {num: card for num, card
			                            in zip(nums, [self._resolution_options[e] for e in picks])}
			self._resolution_picks.clear()
			
			comm = self.interfaces[self.detective]
			await comm.send(f'The police commissioner {self.commissioner.display_name} passed '
			          f'these 2 resolution options to you.')
			for num, option in self._resolution_options.items():
				await comm.send(f'{num}: {option}')
			msg = await comm.send(f'{self.detective.mention}: Specify which resolution to **play** '
			                      'by selecting the corresponding number.')
			
			await self.table.send(f'The police commissioner has removed one resolution '
			                      f'and passed the other two to the detective')
			
			await self.register_reaction_query(msg, self._resolve_resolutions, *nums)
			self._resolution_query = msg
			
			if self._passed_resolutions['red'] == 5:
				await comm.send('If you are unsatisfied with the options, you may suggest to the commissioner to veto. '
				                'If they agree, both resolutions will be discarded and the next round will begin.')
				await comm.send('To request a veto, just type "veto" here.')
				
				# self._queries[comm, self.detective] = self._request_veto
				await self.register_message_query(comm, self.detective, self._request_veto)
			
			self._status = f'Waiting for the detective {self.detective.display_name} to choose which ' \
			               f'resolution should be passed'
			
			return 'done'
	
	
	async def _request_veto(self, message):
		
		if message.clean_content == 'veto':
			
			if message.author == self.detective:
				await self.table.send('The detective has requested to veto these resolutions. '
				                      'The final decision is up to the commissioner.')
				self._status = 'The commissioner must respond to the veto request, ' \
				               'or the detective can choose which resolution to pass.'
				
				comm = self.interfaces[self.commissioner]
				await comm.send('The detective has requested to veto, '
				                'instead of passing one of the resolutions')
				await comm.send(
					f'{self.commissioner.mention}: Either respond with "veto" or "no" depending on if you agree.')
				
				# self._queries[comm, self.commissioner] = self._request_veto
				await self.register_message_query(comm, self.commissioner, self._request_veto)
			
			else:
				await self.table.send('The commissioner and detective have chosen to veto the resolutions.')
				await self.interfaces[self.detective].send('The commissioner agrees to veto the resolution.')
				
				del self._reaction_queries[self._resolution_query]
				self._discard_pile.extend(self._resolution_options.values())
				
				await self._start_new_round()
			
			return 'done'
		
		elif message.clean_content == 'no' and message.author == self.commissioner:
			await self.table.send('The police commissioner has rejected the veto. '
			                      'The detective must select a resolution to pass.')
			await self.interfaces[self.detective].send('The commissioner has rejected the veto. '
			                                            f'{self.detective.mention}: Select one of the resolutions to pass.')
			
			self._status = f'Waiting for the detective {self.detective.display_name} to choose which ' \
			               f'resolution should be passed'
			return 'done'
	
	
	async def _resolve_resolutions(self, reaction, user):
		
		discard = [e for e in self._resolution_options if e != reaction.emoji]
		assert len(discard) == 1
		discard = discard[0]
		self._discard_pile.append(self._resolution_options[discard])
		
		passed = self._resolution_options[reaction.emoji]
		self._passed_resolutions[passed] += 1
		
		await self.table.send(f'A **{passed}** resolution has been passed!')
		await self._check_victory(passed)
		
		await self._check_reshuffle_deck()
		
		if passed == 'red' and self._passed_resolutions['red'] > 0 \
				and self._bonus_rewards[self._passed_resolutions['red'] - 1] is not None:
			
			# [None, 'membership', 'draw', 'pick', 'kill']
			num = self._passed_resolutions['red']
			bonus = self._bonus_rewards[self._passed_resolutions['red'] - 1]
			
			if bonus == 'membership':
				await self.table.send(f'Due to {num} red policies passing, the commissioner must '
				                      f'investigate someone\'s loyalty.')
				comm = self.interfaces[self.commissioner]
				await comm.send(f'{self.commissioner.mention}: Select whose membership to check.')
				self._investigation_options = {p for p in self.players
				                               if p != self.commissioner and p not in self._investigated}
				await comm.send('Options: {}'.format(', '.join(p.display_name for p in self._investigation_options)))
				# self._queries[comm, self.commissioner] = self.
				await self.register_message_query(comm, self.commissioner, self._pick_investigation)
				self._status = 'Waiting for the commissioner to inspect someone\'s loyalty.'
				return 'done'
			
			elif bonus == 'draw':
				await self.table.send(f'Due to {num} red policies passing, the commissioner must '
				                      f'peek at the top three next policies.')
				peek = [self._deck.pop() for _ in range(3)]
				await self.interfaces[self.commissioner].send('The next three policies '
				                                               '(in order of top to bottom): {}'.format(
					', '.join(peek)))
				while len(peek):
					self._deck.append(peek.pop())
			
			elif bonus == 'pick':
				await self.table.send(f'Due to {num} red policies passing, the commissioner must '
				                      f'appoint one player to be the special commissioner candidate.')
				self._pre_special_commissioner = self.commissioner
				
				comm = self.interfaces[self.commissioner]
				await comm.send(
					f'{self.commissioner.mention}: Select someone to be the special police commissioner candidate.')
				self._special_commissioner_options = {p for p in self.players if p != self.commissioner}
				await comm.send(
					'Options: {}'.format(', '.join(p.display_name for p in self._special_commissioner_options)))
				await self.register_message_query(comm, self.commissioner, self._pick_special_commissioner)
				# self._queries[comm, self.commissioner] = self.
				self._status = 'Waiting for the commissioner to pick the special commissioner candidate.'
				return 'done'
			
			elif bonus == 'kill':
				await self.table.send(f'Due to {num} red policies passing, the commissioner must '
				                      f'execute one player (the cops win if it\'s the murderer).')
				
				comm = self.interfaces[self.commissioner]
				await comm.send(f'{self.commissioner.mention}: Select someone to be executed.')
				self._execution_options = {p for p in self.players if p != self.commissioner}
				await comm.send('Options: {}'.format(', '.join(p.display_name for p in self._execution_options)))
				# self._queries[comm, self.commissioner] = self.
				await self.register_message_query(comm, self.commissioner, self._execute_player)
				self._status = 'Waiting for the commissioner to pick someone to kill.'
				return 'done'
			
			else:
				raise Exception(f'unknown bonus: {bonus}')
		
		await self._start_new_round()
		return 'done'
	
	
	async def _pick_special_commissioner(self, message):
		
		# if not len(message.mentions):
		# 	await message.channel.send('You haven\'t mentioned anyone, write "@" followed by a player name')
		#
		# pick = message.mentions[0]
		
		pick = discord.utils.get(self.players, display_name=message.clean_content)
		if pick not in self._investigation_options:
			await message.channel.send('Invalid input, you should input one of these players: {}'
			                           .format(', '.join(p.display_name for p in self._special_commissioner_options)))
			return
		
		await self.table.send(f'{self.commissioner.display_name} has appointed {pick.display_name} to '
		                      f'be the special commissioner candidate')
		
		self._special_commissioner = pick
		await self._start_new_round()
		return 'done'
	
	
	async def _pick_investigation(self, message):
		
		# if not len(message.mentions):
		# 	await message.channel.send('You haven\'t mentioned anyone, write "@" followed by a player name')
		#
		# pick = message.mentions[0]
		
		pick = discord.utils.get(self.players, display_name=message.clean_content)
		if pick not in self._investigation_options:
			await message.channel.send('Invalid input, you should input one of these players: {}'
			                           .format(', '.join(p.display_name for p in self._investigation_options)))
			return
		
		signal = 'a cop.' if self._roles[pick] == 'a cop' else 'a criminal!'
		await self.interfaces[self.commissioner].send(f'{pick.display_name} is {signal}')
		
		await self.table.send(f'The police commissioner has investigated the loyalty of {pick.display_name}')
		
		self._investigated.add(pick)
		await self._start_new_round()
		return 'done'
	
	
	async def _execute_player(self, message):
		
		# if not len(message.mentions):
		# 	await message.channel.send('You haven\'t mentioned anyone, write "@" followed by a player name')
		#
		# pick = message.mentions[0]
		
		pick = discord.utils.get(self.players, display_name=message.clean_content)
		if pick not in self._execution_options:
			await message.channel.send('Invalid input, you should input one of these players: {}'
			                           .format(', '.join(p.display_name for p in self._execution_options)))
			return
		
		await self.table.send(f'The commissioner {self.commissioner.display_name} has executed {pick.display_name}.')
		
		if self._roles[pick] == 'the murderer':
			await self.table.send(f'{pick.display_name} is the murderer! The murderer has been executed!')
			await self._end_game('cops')
		else:
			await self.table.send(f'{pick.display_name} is not the murderer. May they rest in peace.')
			self.players.remove(pick)
			await self._start_new_round()
		return 'done'
	
	
	async def _end_game(self, winner):
		await self.table.send(f'The {winner} have won!')
		self._status = f'The game has ended, the {winner} have won.'
		
		for player, role in self._roles.items():
			await self.table.send(f'{player.display_name} was {role}')
	
	pass

