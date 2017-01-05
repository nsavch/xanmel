import functools
import logging

import asyncio
import random

import geoip2.errors
import math

import requests

from xanmel.modules.xonotic.colors import Color
from xanmel.utils import current_time

logger = logging.getLogger(__name__)


class Player:
    def __init__(self, server, nickname, number1, number2, ip_address):
        self.server = server
        self.nickname = nickname
        self.number1 = number1
        self.number2 = number2
        self.ip_address = ip_address
        self.really_joined = True

        self.join_timestamp = None
        self.geo_response = None
        self.elo_url = None

        self.elo_basic = None
        self.elo_advanced = None
        if not self.is_bot:
            try:
                self.geo_response = self.server.module.xanmel.geoip.city(self.ip_address)
            except (ValueError, geoip2.errors.AddressNotFoundError):
                pass

    async def get_elo(self):
        loop = self.server.module.xanmel.loop
        if self.elo_url is None:
            return
        sig = self.server.config.get('elo_request_signature')
        if not sig:
            return
        retries_left = 3
        while retries_left > 0:
            response = await loop.run_in_executor(None, functools.partial(
                requests.request,
                method='post',
                url=self.elo_url,
                headers={'X-D0-Blind-ID-Detached-Signature': sig},
                data=b'\n'))
            if response.status_code != 404:
                retries_left = 0
            else:
                retries_left -= 1
                logger.debug('404 for %s, %s retries left', self.elo_url, retries_left)
                await asyncio.sleep(1 + random.random() * 2)
        if response.status_code != 200:
            logger.debug('Got status code %s from %s, %s', response.status_code, self.elo_url, response.text)
            return
        try:
            self.parse_elo(response.text)
        except:
            logger.debug('Failed to parse elo %s', response.text, exc_info=True)
        else:
            # logger.debug('Got basic elo %r', self.elo_basic)
            await self.get_elo_advanced()

    async def get_elo_advanced(self):
        loop = self.server.module.xanmel.loop
        url = self.elo_basic.get('url')
        response = await loop.run_in_executor(None, requests.get, url + '.json')
        if response.status_code != 200:
            logger.debug('Got status code %s from %s', response.status_code, self.elo_url)
            return
        try:
            self.elo_advanced = response.json()
            # logger.debug('Got advanced elo %r', self.elo_advanced)
        except:
            logger.debug('Could not parse json %s', response.text, exc_info=True)
        if isinstance(self.elo_advanced, list) and len(self.elo_advanced) > 0:
            self.elo_advanced = self.elo_advanced[0]
        else:
            logger.debug('Strange advanced elo %r', self.elo_advanced)
        if not isinstance(self.elo_advanced, dict):
            logger.debug('Strange advanced elo %r', self.elo_advanced)
            self.elo_advanced = None

    def get_highest_rank(self):
        if not self.elo_advanced:
            return
        highest_rank = None
        for rank in self.elo_advanced.get('ranks', {}).values():
            if rank['game_type_cd'] in self.server.config.get('player_rankings', ['dm', 'duel', 'ctf']):
                if highest_rank is None or rank['percentile'] > highest_rank['percentile']:
                    highest_rank = rank
        return highest_rank

    def parse_elo(self, elo_txt):
        current_mode = None
        elo_data = {}
        for line in elo_txt.split('\n'):
            if not line.strip():
                continue
            pref, data = line.split(' ', 1)
            if current_mode is None and pref not in ('S', 'n', 'i', 'G', 'P'):
                continue
            elif current_mode and pref == 'e':
                elo_data[current_mode] = float(data.strip('elo '))
            if pref == 'S':
                elo_data['url'] = data
            elif pref == 'n':
                elo_data['nickname'] = data
            elif pref == 'i':
                elo_data['player_id'] = int(data)
            elif pref == 'G':
                current_mode = data.lower()
            elif pref == 'P':
                elo_data['primary_id'] = data
        self.elo_basic = elo_data

    @property
    def country(self):
        mode = self.server.config.get('show_geolocation_for', 'none')
        if mode == 'all' or (mode == 'stats-enabled' and self.elo_basic):
            if self.geo_response:
                geoloc = self.geo_response.country.name
            else:
                geoloc = 'Unknown'
        else:
            geoloc = self.server.config.get('private_country', '')
        return geoloc

    def get_server_rank(self):
        if self.elo_basic and self.server.server_stats:
            top_players = self.server.server_stats.get('top_scorers', {}).get('top_scorers', [])
            for i in top_players:
                if self.elo_basic.get('player_id') == i.get('player_id'):
                    return i['rank']

    @property
    def is_bot(self):
        return 'bot' in self.ip_address

    def __str__(self):
        return repr(self.nickname)


class PlayerManager:
    def __init__(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}
        self.elo_data = {}
        self.current_url = None
        self.max = 0

    @property
    def current(self):
        c = 0
        for i in self.players_by_number1.values():
            if not i.is_bot:
                c += 1
        return c

    @property
    def bots(self):
        res = []
        for i in self.players_by_number1.values():
            if i.is_bot:
                res.append(i)
        return res

    def clear_bots(self):
        to_clear = []
        for k, v in self.players_by_number1.items():
            if v.is_bot:
                to_clear.append((k, v.number2))
        for n1, n2 in to_clear:
            try:
                del self.players_by_number1[n1]
                del self.players_by_number2[n2]
            except KeyError:
                pass

    def join(self, player):
        if self.current_url:
            player.elo_url = self.current_url
            self.current_url = None
        if player.number2 in self.players_by_number2:
            old_player = self.players_by_number2[player.number2]
            if old_player.number1 in self.players_by_number1 and self.players_by_number1[old_player.number1].number2 == player.number2:
                del self.players_by_number1[old_player.number1]
            self.players_by_number1[player.number1] = player
            self.players_by_number2[player.number2] = player
            player.really_joined = False
        else:
            self.players_by_number1[player.number1] = player
            self.players_by_number2[player.number2] = player
            player.join_timestamp = current_time()
        return player

    def part(self, number1):
        if number1 in self.players_by_number1:
            player = self.players_by_number1[number1]
            del self.players_by_number1[player.number1]
            if player.number2 in self.players_by_number2:
                del self.players_by_number2[player.number2]
            return player

    def clear(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}

    def get_elo(self, number1, game_type):
        res = '--'
        if number1 in self.players_by_number1:
            player = self.players_by_number1[number1]
            if player.elo_basic:
                res = player.elo_basic.get(game_type, '--')
                if isinstance(res, float):
                    res = math.floor(res)
        return res

    def name_change(self, number1, new_nickname):
        player = self.players_by_number1[number1]
        old_nickname = player.nickname
        player.nickname = new_nickname
        return old_nickname, player

    def __str__(self):
        return ', '.join(['%s: %s' % (n1, Color.dp_to_none(p.nickname).decode('utf8'))
                          for n1, p in self.players_by_number1.items()])
