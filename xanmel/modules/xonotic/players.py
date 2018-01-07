import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote
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

    async def get_db_obj_anon(self):
        raw_nickname = self.nickname.decode('utf8')
        nickname = Color.dp_to_none(self.nickname).decode('utf8')
        query = await self.server.db.mgr.execute(DBPlayer.select().where(DBPlayer.raw_nickname == raw_nickname))
        if len(query) == 1:
            return query[0]
        else:
            return await self.server.db.mgr.create(DBPlayer, raw_nickname=raw_nickname, nickname=nickname)

    async def get_elo(self):
        if self.elo_url is None:
            return
        self.crypto_idfp = self.get_crypto_idfp()
        sig = self.server.config.get('elo_request_signature')
        if not sig:
            return
        retries_left = 3
        async with aiohttp.ClientSession() as session:
            while retries_left > 0:
                async with session.post(self.elo_url,
                                        headers={'X-D0-Blind-ID-Detached-Signature': sig},
                                        data=b'\n') as response:
                    if response.status != 404:
                        retries_left = 0
                    else:
                        retries_left -= 1
                        logger.debug('404 for %s, %s retries left', self.elo_url, retries_left)
                        await asyncio.sleep(1 + random.random() * 2)
                    if retries_left == 0:
                        if response.status != 200:
                            logger.debug('Got status code %s from %s, %s', response.status, self.elo_url,
                                         response.text)
                        else:
                            text = await response.text()
                            try:
                                self.parse_elo(text)
                            except:
                                logger.debug('Failed to parse elo %s', text, exc_info=True)
                            else:
                                # logger.debug('Got basic elo %r', self.elo_basic)
                                await self.update_db()
                                await self.get_elo_advanced()
                        return

    def get_crypto_idfp(self):
        if self.elo_url:
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

        whois = ipwhois.IPWhois(ip_address)
        try:
            result = await self.server.module.xanmel.loop.run_in_executor(ThreadPoolExecutor(), __lookup, whois)
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

    async def get_elo_advanced(self):
        url = self.elo_basic.get('url')
        async with aiohttp.ClientSession() as session:
            async with session.get(url + '.json') as response:
                if response.status != 200:
                    logger.debug('Got status code %s from %s', response.status, self.elo_url)
                    return
                try:
                    self.elo_advanced = await response.json()
                except:
                    logger.debug('Could not parse json %s', response.text, exc_info=True)
        if isinstance(self.elo_advanced, list) and len(self.elo_advanced) > 0:
            self.elo_advanced = self.elo_advanced[0]
        else:
            logger.debug('Strange advanced elo %r', self.elo_advanced)
        if not isinstance(self.elo_advanced, dict):
            logger.debug('Strange advanced elo %r', self.elo_advanced)
            self.elo_advanced = None

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
                # ('wins', __format_num(self.elo_advanced.get('games_played', {}).get('dm', {}).get('win_pct', 0)) + '%'),
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
                self.elo_advanced.get('overall_stats', {}).get('cts', {}).get('total_playing_time_secs', 0)))]
        else:
            return [
                ('games', self.elo_advanced.get('games_played', {}).get('overall', {}).get('games', 0)),
                ('wins',
                 __format_num(self.elo_advanced.get('games_played', {}).get('overall', {}).get('win_pct', 0)) + '%'),
                ('kill/death',
                 __format_num(self.elo_advanced.get('overall_stats', {}).get('overall', {}).get('k_d_ratio', 0)))]

    def parse_elo(self, elo_txt):
        self.elo_basic = parse_elo(elo_txt)

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
