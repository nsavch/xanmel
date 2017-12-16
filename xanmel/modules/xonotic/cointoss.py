import re
from enum import Enum


class CointosserState(Enum):
    PENDING = 0
    ACTIVE = 1
    COMPLETE = 2


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
        self.available_maps = self.pool
        self.selected_maps = []
        self.players = None

    def activate(self, players):
        self.state = CointosserState.ACTIVE
        self.players = players

    def clean_map_name(self, map_name):
        maps = []
        for i in self.available_maps:
            if i.lower().startswith(map_name.lower()):
                maps.append(i)
        if len(maps) == 0:
            raise CointosserException('Map not found: {}'.format(map_name))
        if len(maps) > 1:
            raise CointosserException('Ambiguous map choices {}. Maps matching: {}'.format(map_name, ', '.join(maps)))
        return maps[0]

    def validate_action(self, player, action, map_name):
        current_step = self.steps[self.step_index]
        if self.state != CointosserState.ACTIVE:
            raise CointosserException('Cointoss process is not activated')
        expected_player = self.players[current_step['player'] - 1]
        errors = []
        if player != expected_player:
            errors.append('Expected action from player {}, not from {}'.format(
                expected_player.nickname, player.nickname))

        if action != current_step['action']:
            errors.append('Expected action {}, not {}'.format(
                current_step['action'].value, action.value))
        self.clean_map_name(map_name)
        if errors:
            raise CointosserException(' '.join(errors))

    def format_action_confirmation(self, player, action, map_name):
        self.validate_action(player, action, map_name)
        return '{} is going to {} {}'.format(player.nickname, action.value, self.clean_map_name(map_name))

    def do_action(self, player, action, map_name):
        self.validate_action(player, action, map_name)
        clean_map_name = self.clean_map_name(map_name)
        if action == CointosserAction.P:
            self.selected_maps.append(clean_map_name)
        self.available_maps.remove(clean_map_name)
        if self.step_index == len(self.steps) - 1:
            self.state = CointosserState.COMPLETE
        else:
            self.step_index += 1

    def format_status(self):
        if self.state == CointosserState.PENDING:
            raise CointosserException('Cointoss process is not activated')

        if self.state == CointosserState.COMPLETE:
            res = 'Cointoss complete. Selected maps: {}.'.format(', '.join(self.selected_maps))
        else:
            current_step = self.steps[self.step_index]
            res = 'Selected maps: {}. Available maps: {}. '.format(
                ', '.join(self.selected_maps), ', '.join(self.available_maps))
            expected_player = self.players[current_step['player'] - 1]

            if current_step['action'] == CointosserAction.P:
                res += '{}, please pick a map using /pick <mapname>'.format(expected_player.nickname.decode('utf8'))
            else:
                res += '{}, please drop a map using /drop <mapname>'.format(expected_player.nickname.decode('utf8'))
        return res
