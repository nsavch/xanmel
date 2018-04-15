import asyncio
import logging
from copy import copy
from typing import Dict

import re
from enum import Enum

from xanmel import current_time
from xanmel.modules.xonotic.colors import Color
from xanmel.modules.xonotic.events import CointossChoiceComplete
from xanmel.modules.xonotic.players import Player

logger = logging.getLogger(__name__)


class CointosserState(Enum):
    PENDING = 0
    CHOOSING = 1
    CHOICE_COMPLETE = 2
    PLAYING = 3
    COMPLETE = 4


class CointosserAction(Enum):
    D = 'Drop'
    P = 'Pick'
    S = 'Skip'


class CointosserException(Exception):
    pass


class Cointosser:
    def __init__(self, rcon_server, map_pool, types):
        self.lock = asyncio.Lock()
        self.rcon_server = rcon_server
        if self.rcon_server.config.get('cointoss_log_file'):
            self.log = open(self.rcon_server.config['cointoss_log_file'], 'a')
        else:
            self.log = None
        self.pool = sorted(map_pool)
        self.types = types
        self.switch_type(next(iter(types.keys())))
        self.reset()

    def write_log(self, message):
        t = current_time()
        if self.log:
            self.log.write('{} {}\n'.format(
                t.strftime('%Y-%m-%d %H:%M:%S'),
                message))
            self.log.flush()

    def switch_type(self, new_type):
        self.current_type = new_type
        self.steps = self.parse_steps(self.types[new_type]['steps'])

    def parse_steps(self, steps):
        step_re = re.compile('([Ss]|[Dd]|[Pp])([12])')
        res = []
        for n, i in enumerate(steps):
            m = step_re.match(i)
            if not m:
                raise RuntimeError('Improperly configured: invalid cointoss action {}'.format(i))
            action = CointosserAction[m.group(1).upper()]
            if action == CointosserAction.S and (not n == 0):
                raise RuntimeError('Improperly configured: skip can only be the first action')
            player_num = int(m.group(2))
            res.append({'action': action, 'player': player_num})

        return res

    def reset(self):
        self.step_index = 0
        self.state = CointosserState.PENDING
        self.available_maps = copy(self.pool)
        self.selected_maps = []
        self.skipped_maps = []
        self.players = None
        self.current_map_index = None
        self.scores = []

    def activate(self, players):
        self.state = CointosserState.CHOOSING
        self.players = players
        self.write_log('*****************************************************************')
        self.write_log('{} vs {}, cointoss won by {}'.format(
            Color.dp_to_none(self.players[0].nickname).decode('utf8'),
            Color.dp_to_none(self.players[1].nickname).decode('utf8'),
            Color.dp_to_none(self.players[0].nickname).decode('utf8'),
        ))

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
            self.write_log('{} picked {}'.format(
                Color.dp_to_none(player.nickname).decode('utf8'),
                clean_map_name
            ))
        elif action == CointosserAction.D:
            self.write_log('{} dropped {}'.format(
                Color.dp_to_none(player.nickname).decode('utf8'),
                clean_map_name
            ))
        elif action == CointosserAction.S:
            self.write_log('{} skipped {}'.format(
                Color.dp_to_none(player.nickname).decode('utf8'),
                clean_map_name
            ))
            self.skipped_maps.append(clean_map_name)
            self.selected_maps.append(clean_map_name)
        self.available_maps.remove(clean_map_name)
        if self.step_index == len(self.steps) - 1:
            self.state = CointosserState.CHOICE_COMPLETE
            CointossChoiceComplete(self.rcon_server.module, server=self.rcon_server).fire()
        elif len(self.available_maps) == 1 and \
                self.step_index == len(self.steps) - 2 and \
                self.steps[-1]['action'] == CointosserAction.P:
            self.state = CointosserState.CHOICE_COMPLETE
            self.selected_maps += self.available_maps
            CointossChoiceComplete(self.rcon_server.module, server=self.rcon_server).fire()
        else:
            self.step_index += 1

    def format_current_score(self):
        games, frags = self.get_total_score()
        game_scores = []
        for s1, s2 in self.scores:
            game_scores.append('^2{}^5:^2{}^7'.format(s1, s2))
        return '^2Score ^7(^1{type}^7): ^7{player1} - {player2}: ^2{games1}^5:^2{games2} ^7(^2{game_scores})^7'.format(
            type=self.current_type,
            player1=self.players[0].nickname.decode('utf8'),
            player2=self.players[1].nickname.decode('utf8'),
            games1=games[0],
            games2=games[1],
            game_scores='^7, ^2'.join(game_scores)
        )

    def format_status(self):
        # TODO: forward status to IRC too
        if self.state == CointosserState.PENDING:
            res = ['^3Cointoss is not activated^7. ^3Current cointoss type: ^1{}^7. ^2/cointoss heads^5|^2tails ^3to start it.'.format(
                self.current_type
            )]
        elif self.state == CointosserState.CHOICE_COMPLETE:
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
                res.append('^3Available maps: ^2{}^7.'.format('^7, ^2'.join(self.available_maps)))
            expected_player = self.players[current_step['player'] - 1]

            if current_step['action'] == CointosserAction.P:
                res.append('^7{}, ^3please ^2pick^3 a map using ^2/pick ^5<mapname>'.format(expected_player.nickname.decode('utf8')))
            elif current_step['action'] == CointosserAction.D:
                res.append('^7{}, ^3please ^1drop^3 a map using ^1/drop ^5<mapname>'.format(expected_player.nickname.decode('utf8')))
            elif current_step['action'] == CointosserAction.S:
                res.append('^7{}, ^3please ^5skip^3 a map using ^5/skip ^5<mapname>'.format(
                    expected_player.nickname.decode('utf8')))
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
        for i in self.skipped_maps:
            self.rcon_server.say('^3{} gets a free win on {}^7'.format(
                self.players[0].nickname.decode('utf8'),
                i
            ))
            self.scores.append((0, -10))
            self.current_map_index += 1
        self.gotomap()

    async def map_ended(self, map_name: str, scores: Dict[Player, int]) -> None:
        if self.selected_maps[self.current_map_index] != map_name:
            self.rcon_server.say('Expected map {}, got map {}'.format(self.selected_maps[self.current_map_index],
                                                                      map_name))
            await asyncio.sleep(1)
            self.rcon_server.say(self.format_status())
            await asyncio.sleep(3)
            self.gotomap()
            return
        if len(scores) != 2:
            self.rcon_server.say('Got scores with {} players, expected a duel!'.format(len(scores)))
            await asyncio.sleep(1)
            self.rcon_server.say(self.format_status())
            await asyncio.sleep(3)
            self.gotomap()
            return
        if int(self.rcon_server.cvars['xanmel_wup_stage']) == 1:
            self.rcon_server.say('Match ended during warmup stage, restarting!')
            await asyncio.sleep(1)
            self.rcon_server.say(self.format_status())
            await asyncio.sleep(3)
            self.gotomap()
            return

        players = list(scores.keys())

        def __player_is(pl1, pl2):
            logger.debug(repr(pl1.crypto_idfp), repr(pl1.nickname), repr(pl2.crypto_idfp), repr(pl2.nickname))
            return (pl1.crypto_idfp and pl1.crypto_idfp == pl2.crypto_idfp) or \
                   (pl1.crypto_idfp is None and pl1.nickname == pl2.nickname)

        for i in players:
            if not (__player_is(i, self.players[0]) or __player_is(i, self.players[1])):
                self.rcon_server.say('Unexpected player {}, expected {} and {}! Restarting.'.format(
                    i.nickname.decode('utf8'),
                    self.players[0].nickname.decode('utf8'),
                    self.players[1].nickname.decode('utf8')
                ))
                await asyncio.sleep(1)
                self.rcon_server.say(self.format_status())
                await asyncio.sleep(3)
                self.gotomap()
                return

        if __player_is(players[0], self.players[0]):
            frags = (scores[players[0]], scores[players[1]])
        else:
            frags = (scores[players[1]], scores[players[0]])

        if frags[0] == frags[1]:
            self.rcon_server.say('Scores are equal, expected a winner! Restarting.')
            await asyncio.sleep(1)
            self.rcon_server.say(self.format_status())
            await asyncio.sleep(3)
            self.gotomap()
            return
        self.scores.append(tuple(frags))
        self.write_log('{}: {} - {}, {} - {}'.format(
            map_name,
            Color.dp_to_none(self.players[0].nickname).decode('utf8'),
            frags[0],
            Color.dp_to_none(self.players[1].nickname).decode('utf8'),
            frags[1]))
        games, _ = self.get_total_score()
        if (max(games) > len(self.selected_maps) / 2) or (self.current_map_index == len(self.selected_maps) - 1):
            self.write_log('Match completed')
            self.write_log('*****************************************************************')
            self.state = CointosserState.COMPLETE
            self.rcon_server.say(self.format_status())
            await asyncio.sleep(5)
        else:
            self.current_map_index += 1
            self.write_log('Switching to map {}'.format(self.selected_maps[self.current_map_index]))
            self.rcon_server.say(self.format_status())
            self.rcon_server.say('^2Switching to map ^5{} ^2in ^35 ^2seconds^7'.format(self.selected_maps[self.current_map_index]))
            await asyncio.sleep(5)
            self.gotomap()
