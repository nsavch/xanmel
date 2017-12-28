import asyncio
from copy import copy
from typing import Dict

import re
from enum import Enum

from xanmel.modules.xonotic.events import CointossChoiceComplete
from xanmel.modules.xonotic.players import Player


class CointosserState(Enum):
    PENDING = 0
    CHOOSING = 1
    CHOICE_COMPLETE = 2
    PLAYING = 3
    COMPLETE = 4


class CointosserAction(Enum):
    D = 'Drop'
    P = 'Pick'


class CointosserException(Exception):
    pass


class Cointosser:
    def __init__(self, rcon_server, map_pool, steps):
        self.rcon_server = rcon_server
        self.pool = sorted(map_pool)
        self.steps = []
        self.parse_steps(steps)
        self.reset()

    def parse_steps(self, steps):
        step_re = re.compile('([Dd]|[Pp])([12])')
        for i in steps:
            m = step_re.match(i)
            if not m:
                raise RuntimeError('Improperly configured: invalid cointoss action {}'.format(i))
            action = CointosserAction[m.group(1).upper()]
            player_num = int(m.group(2))
            self.steps.append({'action': action, 'player': player_num})

    def reset(self):
        self.step_index = 0
        self.state = CointosserState.PENDING
        self.available_maps = copy(self.pool)
        self.selected_maps = []
        self.players = None
        self.current_map_index = None
        self.scores = []

    def activate(self, players):
        self.state = CointosserState.CHOOSING
        self.players = players

    def clean_map_name(self, map_name):
        maps = []
        for i in self.available_maps:
            if i.lower().startswith(map_name.lower()):
                maps.append(i)
        if len(maps) == 0:
            raise CointosserException('^3Map not found^7: ^1{map}^7'.format(map=map_name))
        if len(maps) > 1:
            raise CointosserException('^1Ambiguous map choice ^3{prefix}^7. ^2Maps matching: ^3{maps}^7'.format(
                prefix=map_name,
                maps='^7, ^3'.join(maps)))
        return maps[0]

    def validate_action(self, player, action, map_name):
        current_step = self.steps[self.step_index]
        if self.state != CointosserState.CHOOSING:
            raise CointosserException('^3Cointoss has not yet started^7')
        expected_player = self.players[current_step['player'] - 1]
        errors = []
        if player != expected_player:
            errors.append('^3Expected action from player ^2{expected_player}^7, ^3not from ^2{player}^7'.format(
                expected_player=expected_player.nickname.decode('utf8'),
                player=player.nickname.decode('utf8')))

        if action != current_step['action']:
            errors.append('^3Expected ^2{expected_action}^7, ^3not ^2{provided_action}^7'.format(
                expected_action=current_step['action'].value,
                provided_action=action.value))
        self.clean_map_name(map_name)
        if errors:
            raise CointosserException(' '.join(errors))

    def do_action(self, player, action, map_name):
        self.validate_action(player, action, map_name)
        clean_map_name = self.clean_map_name(map_name)
        if action == CointosserAction.P:
            self.selected_maps.append(clean_map_name)
        self.available_maps.remove(clean_map_name)
        if self.step_index == len(self.steps) - 1:
            self.state = CointosserState.CHOICE_COMPLETE
            CointossChoiceComplete(self.rcon_server.module, server=self.rcon_server).fire()
        else:
            self.step_index += 1

    def format_current_score(self):
        games, frags = self.get_total_score()
        return '^2Score: ^7{player1} - ^2{games1} ^5({frags1} frags)^7, {player2} - ^2{games2} ^5({frags2} frags)^7'.format(
            player1=self.players[0].nickname.decode('utf8'),
            player2=self.players[1].nickname.decode('utf8'),
            games1=games[0],
            games2=games[1],
            frags1=frags[0],
            frags2=frags[1])

    def format_status(self):
        # TODO: forward status to IRC too
        if self.state == CointosserState.PENDING:
            raise CointosserException('^3Cointoss has not yet started^7')

        if self.state == CointosserState.CHOICE_COMPLETE:
            res = ['^2Cointoss complete. ^3Selected maps: ^5{maps}^7.'.format(maps='^7, ^5'.join(self.selected_maps))]
        elif self.state == CointosserState.PLAYING:

            res = [self.format_current_score()]
            status = ''
            finished_maps = self.selected_maps[:self.current_map_index]
            if finished_maps:
                status += '^3Finished maps: ^5{}^7.'.format('^7, ^5'.join(finished_maps))
            status += ' ^3Current map: ^2{}^7.'.format(self.selected_maps[self.current_map_index])
            next_maps = self.selected_maps[self.current_map_index + 1:]
            if next_maps:
                status += ' ^3Remaining: ^5{}^7.'.format('^7, ^5'.join(next_maps))
            res.append(status)

        elif self.state == CointosserState.COMPLETE:
            res = ['^2Match finished!^7', self.format_current_score()]
        else:
            current_step = self.steps[self.step_index]
            res = []
            if self.selected_maps:
                res.append('^3Selected maps: ^5{}^7.'.format('^7, ^5'.join(self.selected_maps)))
            if self.available_maps:
                res.append('^3Available maps: ^2{}^7.'.format('^7, ^5'.join(self.available_maps)))
            expected_player = self.players[current_step['player'] - 1]

            if current_step['action'] == CointosserAction.P:
                res.append('^7{}, ^3please pick a map using ^2/pick ^5<mapname>'.format(expected_player.nickname.decode('utf8')))
            else:
                res.append('^7{}, ^3please drop a map using ^2/drop ^5<mapname>'.format(expected_player.nickname.decode('utf8')))
        return res

    def get_total_score(self):
        games = (0, 0)
        frags = (0, 0)
        for f1, f2 in self.scores:
            frags = (frags[0] + f1, frags[1] + f2)
            if f1 > f2:
                games = (games[0] + 1, games[1])
            else:
                games = (games[0], games[1] + 1)
        return games, frags

    def gotomap(self):
        self.rcon_server.send('gotomap {}'.format(self.selected_maps[self.current_map_index]))

    def start_playing(self):
        self.current_map_index = 0
        self.gotomap()

    async def map_ended(self, map_name: str, scores: Dict[Player, int]) -> None:
        if self.selected_maps[self.current_map_index] != map_name:
            # FIXME: HOW TO HANDLE THIS?
            self.gotomap()
            return
        if len(scores) != 2:
            # FIXME: HOW TO HANDLE THIS?
            self.gotomap()
            return
        frags = [0, 0]
        players = list(scores.keys())
        if not (players[0].crypto_idfp and players[1].crypto_idfp):
            # TODO: TEST THIS CASE!!!
            if players[0].nickname == self.players[0].nickname:
                frags = (scores[players[0]], scores[players[1]])
            else:
                frags = (scores[players[1]], scores[players[0]])
        elif players[0].crypto_idfp:
            if players[0].crypto_idfp == self.players[0].crypto_idfp:
                frags = (scores[players[0]], scores[players[1]])
            else:
                frags = (scores[players[1]], scores[players[0]])
        else:
            if players[1].crypto_idfp == self.players[1].crypto_idfp:
                frags = (scores[players[0]], scores[players[1]])
            else:
                frags = (scores[players[1]], scores[players[0]])
        print(scores)
        print(frags)
        self.scores.append(tuple(frags))
        games, _ = self.get_total_score()
        if (max(games) > len(self.selected_maps) / 2) or (self.current_map_index == len(self.selected_maps) - 1):
            self.state = CointosserState.COMPLETE
            self.rcon_server.say(self.format_status())
            await asyncio.sleep(5)
        else:
            self.current_map_index += 1
            self.rcon_server.say(self.format_status())
            self.rcon_server.say('^2Switching to map ^5{} ^2in ^35 ^2seconds^7'.format(self.selected_maps[self.current_map_index]))
            await asyncio.sleep(5)
            self.gotomap()
