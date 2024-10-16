import json
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote, quote
import asyncio

import datetime
import random

import geoip2.errors
import math
import aiohttp
import peewee
import ipwhois

from xanmel.modules.xonotic.colors import Color
from xanmel.utils import current_time

from .models import Player as DBPlayer, PlayerAccount, PlayerIdentification

logger = logging.getLogger(__name__)

ELO_REQUEST_SIGNATURE = 'gQEBTrBWi2M7i5cInTMatx0iHAxmN4Xta2NZdXD2OsFls/x/k6XrxoevCGARC4jhC2DzgYHFM5vA40aih59tlXSzrFQ6EiiSgoWG+h1oERFHYWdg3KNwgEkUfnskEy2FS6BhdTs6JdpBAsEq348+NysGVhe7ZYMHlJUTFYE/nJVKC4qBAQGPqnGoD6GhuHLYN+Sf73ROColneBdJ7ttuVwm32FvI8LuD5aLDll7bpqfHTWhgbTW02CYvkTAYtoz2RZmIGK5ZHHaM/V6vcSXnq2ab/7mFRiag7D5OUsmIFY9E3IqcqtP7+wXSVgiNFY3DBPy27bXjk8ZJ9nUD5dQBL9sG8TzWd4EBAdZmc6gLKdO16z5PJQGsWrf1yOViENd/VANx+7aGPQsouAuhwzOlB06SkZ6dxx2zLyfagVthXTXY4JfUoAaa9vSkwqH/7TNIyHxBI220ZyFtekGzJFro2b7zRYiOqs3bKr0pec7qakn9blY0YfgO9W9GI8vG+JsQIk7MJNmSBupTgQEBQUDrksY28iujDepIsG4mXaZdvKM2RhWKKxI4VgrXQ33FVmAQqPwrA3U0EMEE6DR+O8tf6kHsN5efub9aU30E5nRcKEKBln5ro3RHtnLMtBikG5Tqy4o3grx4/SHfFPhs4CMvOYT304A6y1f35TsUj83ahbORkFjaKetTq97vZkk='


def parse_elo(elo_txt):
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
    return elo_data


class Player:
    def __init__(self, server, nickname, number1, number2, ip_address):
        self.server = server
        self.nickname = nickname
        self.number1 = number1
        self.number2 = number2
        self.ip_address = ip_address
        self.really_joined = True

        self.join_timestamp = None
        self.elo_url = None

        self.elo_basic = None
        self.elo_advanced = None
        self.player_db_obj = None
        self.account = None
        self.crypto_idfp = None
        if not self.is_bot:
            try:
                self.geo_response = self.server.module.xanmel.geoip.city(self.ip_address)
            except (ValueError, geoip2.errors.AddressNotFoundError):
                self.geo_response = None

    @property
    def active(self):
        return self in self.server.players.active

    async def get_db_obj_anon(self):
        raw_nickname = self.nickname.decode('utf8')
        nickname = Color.dp_to_none(self.nickname).decode('utf8')
        query = await self.server.db.mgr.execute(DBPlayer.select().where(DBPlayer.raw_nickname == raw_nickname))
        if len(query) == 1:
            return query[0]
        else:
            return await self.server.db.mgr.create(DBPlayer, raw_nickname=raw_nickname, nickname=nickname)

    async def get_elo(self):
        self.crypto_idfp = await self.server.prvm_edictget(self.number2, 'crypto_idfp')
        if self.crypto_idfp is not None:
            self.crypto_idfp = self.crypto_idfp.strip()
        if not self.crypto_idfp:
            return
        quoted_crypto_idfp = quote(self.crypto_idfp, safe='')
        self.elo_url = 'https://stats.xonotic.org/skill?hashkey={}'.format(quoted_crypto_idfp)
        retries_left = 3
        logger.debug('Starting to get elo for %r (%r)', self.nickname, self.elo_url)
        async with aiohttp.ClientSession() as session:
            while retries_left > 0:
                async with session.get(
                        self.elo_url,
                        allow_redirects=True,
                        headers={'Accept': 'application/json'}
                ) as response:
                    if response.status != 200:
                        retries_left -= 1
                        logger.debug('404 for %s, %s retries left', self.elo_url, retries_left)
                        await asyncio.sleep(1 + random.random() * 2)
                        continue
                    else:
                        data = await response.json()
                        logger.debug('Got skill data for %r: %s', self.nickname, data)

                        self.elo_basic = {}
                        got_player_id = False
                        for i in data:
                            if 'player_id' in i:
                                self.elo_basic['player_id'] = i['player_id']
                                got_player_id = True
                            if 'game_type_cd' in i:
                                self.elo_basic[i['game_type_cd']] = i.get('mu', 0) - i.get('sigma', 0) * 3
                        if not got_player_id:
                            self.elo_basic['player_id'] = None
                        if self.server.db.is_up:
                            await self.update_db()
                        logger.debug('DB updated for %r', self.nickname)
                        if self.elo_basic['player_id'] is not None:
                            player_data_url = 'https://stats.xonotic.org/player/{}'.format(self.elo_basic['player_id'])
                            logger.debug('Player URL: %s', player_data_url)
                            async with aiohttp.ClientSession() as session1:
                                async with session1.get(
                                        player_data_url,
                                        headers={'Accept': 'application/json'},
                                ) as response1:
                                    if response1.status == 200:
                                        try:
                                            data = await response1.text()
                                            data_json = json.loads(data)
                                            logger.debug('Got advanced elo %s', data_json)
                                            self.elo_advanced = data_json
                                        except:
                                            logger.debug('Got strange response for player data %s', await response1.text())
                        return

    def get_crypto_idfp(self):
        if self.crypto_idfp:
            return self.crypto_idfp
        elif self.elo_url:
            return unquote(unquote(unquote(self.elo_url.split('/')[-2])))  # Triple urlquote, how cool is that?
        else:
            return None

    async def update_db(self):
        crypto_idfp = self.get_crypto_idfp()
        stats_id = self.elo_basic['player_id']
        nickname = Color.dp_to_none(self.nickname).decode('utf8')
        raw_nickname = self.nickname.decode('utf8')
        try:
            player_obj = await self.server.db.mgr.get(
                DBPlayer, DBPlayer.stats_id == stats_id or DBPlayer.crypto_idfp == crypto_idfp)
        except peewee.DoesNotExist:
            player_obj = await self.server.db.mgr.create(DBPlayer, crypto_idfp=crypto_idfp, stats_id=stats_id,
                                                         nickname=nickname, raw_nickname=raw_nickname)
        else:
            player_obj.crypto_idfp = crypto_idfp
            player_obj.nickname = nickname
            player_obj.raw_nickname = raw_nickname
            await self.server.db.mgr.update(player_obj)

        try:
            self.account = await self.server.db.mgr.get(PlayerAccount, PlayerAccount.player == player_obj)
        except peewee.DoesNotExist:
            self.account = await self.server.db.mgr.create(PlayerAccount, player=player_obj)
        self.player_db_obj = player_obj

    async def get_whois(self, ip_address):
        def __lookup(w):
            try:
                return w.lookup_rdap(retry_count=10)
            except:
                return {}
        import time
        t = time.time()
        whois = ipwhois.IPWhois(ip_address)
        try:
            result = await self.server.module.xanmel.loop.run_in_executor(ThreadPoolExecutor(), __lookup, whois)
            logger.debug('Whois took %s', time.time() - t)
            return result
        except:
            return {}

    async def update_identification(self):
        if self.server.db.is_up:
            whois_response = await self.get_whois(self.ip_address)
            data = PlayerIdentification.whois(whois_response)
            data.update(PlayerIdentification.geolocate(self.geo_response))
            await self.server.db.mgr.create(PlayerIdentification,
                                            server=self.server.server_db_obj,
                                            player=self.player_db_obj,
                                            crypto_idfp=self.get_crypto_idfp(),
                                            stats_id=self.elo_basic and self.elo_basic.get('player_id'),
                                            ip_address=self.ip_address,
                                            raw_nickname=self.nickname.decode('utf8'),
                                            nickname=Color.dp_to_none(self.nickname).decode('utf8'),
                                            **data)

    def get_mode_stats(self):
        def __format_num(n):
            return '{:.2f}'.format(n)

        def __format_time(t):
            td = datetime.timedelta(seconds=t)
            return str(td)

        if not self.elo_advanced:
            return []

        if self.server.stats_mode == 'dm':
            return [
                ('games', self.elo_advanced.get('games_played', {}).get('dm', {}).get('games', 0)),
                ('wins', __format_num(self.elo_advanced.get('games_played', {}).get('dm', {}).get('win_pct', 0)) + '%'),
                ('kill/death',
                 __format_num(self.elo_advanced.get('overall_stats', {}).get('dm', {}).get('k_d_ratio', 0)))]
        elif self.server.stats_mode == 'duel':
            return [
                ('games', self.elo_advanced.get('games_played', {}).get('duel', {}).get('games', 0)),
                ('wins',
                 __format_num(self.elo_advanced.get('games_played', {}).get('duel', {}).get('win_pct', 0)) + '%'),
                ('kill/death',
                 __format_num(self.elo_advanced.get('overall_stats', {}).get('duel', {}).get('k_d_ratio', 0)))]
        elif self.server.stats_mode == 'cts':
            return [
                ('games', self.elo_advanced.get('games_played', {}).get('cts', {}).get('games', 0)),
                ('time played', __format_time(
                self.elo_advanced.get('overall_stats', {}).get('cts', {}).get('total_playing_time', 0)))]
        else:
            return [
                ('games', self.elo_advanced.get('games_played', {}).get('overall', {}).get('games', 0)),
                ('wins',
                 __format_num(self.elo_advanced.get('games_played', {}).get('overall', {}).get('win_pct', 0)) + '%'),
                ('kill/death',
                 __format_num(self.elo_advanced.get('overall_stats', {}).get('overall', {}).get('k_d_ratio', 0)))]

    @property
    def country(self):
        mode = self.server.config.get('show_geolocation_for', 'none')
        if mode == 'all' or (mode == 'stats-enabled' and
                             self.elo_basic and
                             self.elo_basic.get('player_id') not in self.server.config.get(
                    'disable_geolocation_for')):
            if self.geo_response:
                geoloc = self.geo_response.country.name
            else:
                geoloc = 'Unknown'
        else:
            geoloc = self.server.config.get('private_country', '')
        return geoloc

    def get_server_rank(self):
        if self.elo_basic and self.server.server_rating:
            for i in self.server.server_rating:
                if self.elo_basic.get('player_id') == i.get('player_id'):
                    return i['rank'], len(self.server.server_rating)

    @property
    def is_bot(self):
        return 'bot' in self.ip_address

    def __str__(self):
        return repr(self.nickname)


class PlayerManager:
    def __init__(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}
        self.status = {}
        self.elo_data = {}
        self.current_url = None
        self.max = 0

    @property
    def active(self):
        res = []
        for n2, v in self.status.items():
            if n2 in self.players_by_number2 and v['frags'] != -666:
                res.append(self.players_by_number2[n2])
        return res

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

    def find_by_nickname(self, nickname):
        for i in self.players_by_number2.values():
            if i.nickname == nickname:
                return i

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
            player.elo_url = self.current_url.decode('utf8')
            self.current_url = None
        if player.number2 in self.players_by_number2:
            old_player = self.players_by_number2[player.number2]
            if old_player.number1 in self.players_by_number1 and self.players_by_number1[
                old_player.number1].number2 == player.number2:
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
            if player.number2 in self.status:
                del self.status[player.number2]
            return player

    def clear(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}
        self.status = {}

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
