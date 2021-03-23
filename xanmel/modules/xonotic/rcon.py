from typing import Union

import re
import time
import asyncio
import logging

import aiohttp
import peewee
from aio_dprcon.client import RconClient
from aio_dprcon.protocol import RCON_SECURE_TIME

from xanmel.modules.xonotic.cointoss import Cointosser
from xanmel.modules.xonotic.events import ServerDisconnect, ServerConnect
from xanmel.modules.xonotic.rcon_cmd import RconCmdParser
from xanmel.utils import current_time
from .rcon_log import RconLogParser
from .players import PlayerManager
from .chat_commands import XonCommands
from .models import MapRating, Server, Map

logger = logging.getLogger(__name__)


class MapVoter:
    def __init__(self, server):
        self.server = server
        self.map_name = ''
        self.votes = {}  # number2 -> vote

    async def store(self, new_map_name):
        db = self.server.module.xanmel.db
        ts = current_time()
        map_name = self.map_name
        self.map_name = new_map_name
        if not db.is_up:
            return
        if len(self.votes) == 0:
            return
        map, _ = await db.mgr.get_or_create(Map, server=self.server.server_db_obj, name=map_name)
        logger.debug('GOING TO STORE VOTES %s:%r', ts, self.votes)
        for vote in self.votes.values():
            if vote['player'].player_db_obj is None:
                player = await vote['player'].get_db_obj_anon()
            else:
                player = vote['player'].player_db_obj
            await db.mgr.create(
                MapRating,
                map=map,
                player=player,
                vote=vote['vote'],
                message=vote['message'])
        self.votes = {}


class RconServer(RconClient):
    def __init__(self, module, config):
        self.module = module
        self.db = self.module.xanmel.db
        self.loop = module.loop
        self.config = config
        self.server_address = config['rcon_ip']
        self.server_port = int(config['rcon_port'])
        self.log_listener_ip = config['log_listener_ip']
        self.password = config['rcon_password']
        self.secure = int(config.get('rcon_secure', RCON_SECURE_TIME))
        super().__init__(self.loop, self.server_address, self.server_port,
                         password=self.password, secure=self.secure,
                         log_listener_ip=self.log_listener_ip)
        self.log_parser = RconLogParser(self)
        self.cmd_parser = RconCmdParser(self)
        self.disabled = config.get('disabled', False)
        self.players = PlayerManager()
        self.current_map = ''
        self.current_gt = ''
        self.timing = ''
        self.server_rating = []
        self.local_cmd_root = None
        self.command_container = XonCommands(rcon_server=self)
        self.command_container.help_text = 'Commands for interacting with %s' % config['name']
        if config.get('raw_log'):
            self.raw_log = open(config['raw_log'], 'ab')
        else:
            self.raw_log = None
        self.map_list = []
        self.dyn_fraglimit_lock = asyncio.Lock()
        self.game_start_timestamp = 0
        self.map_voter = MapVoter(self)
        if config.get('cointoss_map_pool'):
            self.cointosser = Cointosser(self, config['cointoss_map_pool'], config['cointoss_types'])
        else:
            self.cointosser = None
        self.active_vote = None
        self.server_db_obj = None
        self.active_duel_pair = None
        self.betting_odds = None
        self.betting_session_id = None
        self.betting_session = None
        self.betting_session_active = False
        self.forward_chat_to_other_servers = config.get('forward_chat_to_other_servers', [])
        self.display_in_game_info = config.get('display_in_game_info', True)
        self.stats_mode = config.get('stats_mode', 'overall')

    @property
    def host(self):
        return self.status.get('host')

    def on_server_connected(self):
        super().on_server_connected()
        self.loop.create_task(asyncio.wait([self.update_maplist(),
                                            self.update_server_name(),
                                            self.update_server_stats()]))
        ServerConnect(self.module, server=self).fire()

    def on_server_disconnected(self):
        super().on_server_disconnected()
        ServerDisconnect(self.module, server=self).fire()

    def custom_log_callback(self, data, addr):
        if self.raw_log:
            self.raw_log.write(data)

    async def update_maplist(self):
        self.cvars['g_maplist'] = None
        await self.execute_with_retry('g_maplist', lambda: bool(self.cvars['g_maplist']))
        self.map_list = sorted(self.cvars['g_maplist'].split(' '))
        logger.info('Got %s on the map list', len(self.map_list))
        logger.debug(self.map_list)

    async def update_server_status(self):
        res = await super().update_server_status()
        if res:
            m = re.match(r'(\d+)\s*active\s*\((\d+)\s*max', self.status['players'])
            if m:
                self.players.max = int(m.group(2))
            self.command_container.help_text = 'Commands for interacting with %s' % self.status['host']
            to_remove = []
            for n2, v in self.players.status.items():
                if time.time() - v['timestamp'] > self.poll_status_interval * 3:
                    to_remove.append(n2)
            for n2 in to_remove:
                del self.players.status[n2]
            self.send('prvm_globalget server warmup_stage _xanmel_wup_stage')
            await asyncio.sleep(0.1)
            self.send('_xanmel_wup_stage')
            # for n2, v in self.players.status.items():
            #     logger.debug('%s: %s', n2, v)
        return res

    async def update_server_stats(self):
        # doesn't work with new xonstats API :(
        # if self.config.get('server_stats_url'):
        #     self.server_rating = []
        #     while True:
        #         async with aiohttp.ClientSession() as session:
        #             async with session.get(self.config['server_stats_url'] + ('/topscorers?last=%s' % len(self.server_rating)),
        #                                    headers={'Accept': 'application/json'}) as resp:
        #                 if resp.status != 200:
        #                     logger.info('Could not download server stats from %s, got status %s',
        #                                 self.config.get['server_stats_url'],
        #                                 resp.status)
        #                     return
        #                 try:
        #                     players = await resp.json()
        #                     if len(players.get('top_scorers', [])) == 0:
        #                         break
        #                     else:
        #                         self.server_rating += players['top_scorers']
        #                 except:
        #                     logger.info('Could not parse stats', exc_info=True)
        return

    async def update_server_name(self):
        if not self.db.is_up:
            return
        try:
            srv = await self.db.mgr.get(Server, id=self.config['unique_id'])
        except peewee.DoesNotExist:
            srv = await self.db.mgr.create(Server, id=self.config['unique_id'], config_name=self.config['name'], name=self.status['host'])
        else:
            srv.name = self.status['host']
            await self.db.mgr.update(srv)
        self.server_db_obj = srv

    def say_ircmsg(self, message: Union[str, list, tuple], nick: str=None) -> None:
        if isinstance(message, str):
            message = [message]
        for i in message:
            if nick:
                self.send('sv_cmd ircmsg {}^7: {}'.format(nick, i))
            else:
                self.send('sv_cmd ircmsg ^7{}'.format(i))

    def say_say(self, message: Union[str, list, tuple], nick: str=None) -> None:
        if isinstance(message, str):
            message = [message]
        for i in message:
            if nick:
                with self.sv_adminnick(nick):
                    self.send('say {}'.format(i))
            else:
                with self.sv_adminnick(self.config.get('botnick', 'server')):
                    self.send('say {}'.format(i))

    def say(self, message: Union[str, list, tuple], nick: str=None) -> None:
        if self.config['say_type'] == 'ircmsg':
            self.say_ircmsg(message, nick)
        else:
            self.say_say(message, nick)

    async def prvm_edictget(self, entity_id, variable, program_name='server'):
        internal_variable = '_xanmel_{}_{}_{}'.format(program_name, entity_id, variable)
        self.send('prvm_edictget {} {} {} {}'.format(
            program_name,
            entity_id,
            variable,
            internal_variable
        ))
        self.cvars.pop(internal_variable, None)
        await self.execute_with_retry(internal_variable,
                                      lambda: internal_variable in self.cvars)
        return self.cvars[internal_variable]


