import http.client
from collections import defaultdict
from urllib.parse import quote

from echoices import EChoice
from peewee import *
from playhouse.postgres_ext import BinaryJSONField

from xanmel import current_time
from xanmel.db import BaseModel
from xanmel.modules.xonotic.colors import Color


class Server(BaseModel):
    name = CharField(null=True)
    config_name = CharField()


class Player(BaseModel):
    crypto_idfp = CharField(index=True, null=True)
    stats_id = IntegerField(index=True, null=True)
    raw_nickname = CharField()
    nickname = CharField()

    @classmethod
    def from_cryptoidfp(cls, crypto_idfp, elo_request_signature):
        from xanmel.modules.xonotic.players import parse_elo

        try:
            return cls.get(cls.crypto_idfp == crypto_idfp)
        except DoesNotExist:
            con = http.client.HTTPConnection('stats.xonotic.org')
            url = '/player/%s/elo.txt' % quote(quote(quote(crypto_idfp)))
            con.request('POST', url, body=b'\n',
                        headers={'X-D0-Blind-ID-Detached-Signature': elo_request_signature})
            resp = con.getresponse()
            if resp.status == 200:
                data = resp.read().decode('utf8')
                elo_data = parse_elo(data)
                return cls.create(crypto_idfp=crypto_idfp, stats_id=elo_data['player_id'],
                                  raw_nickname=elo_data['nickname'],
                                  nickname=Color.dp_to_none(elo_data['nickname'].encode('utf8')).decode('utf8'))


class Map(BaseModel):
    name = CharField(index=True)
    server = ForeignKeyField(Server)
    thumbnail_url = CharField(null=True)


class MapRating(BaseModel):
    map = ForeignKeyField(Map)
    player = ForeignKeyField(Player)
    timestamp = DateTimeField(default=current_time)
    vote = IntegerField()
    message = CharField()

    class Meta:
        db_table = 'map_rating'

    def __repr__(self):
        return 'MapRating(nickname=%r, map=%r, vote=%r)' % (self.player, self.map, self.vote)


class CalledVote(BaseModel):
    map = ForeignKeyField(Map)
    player = ForeignKeyField(Player)
    timestamp = DateTimeField(default=current_time)
    vote_type = CharField(index=True)
    time_since_round_start = IntegerField()

    class Meta:
        db_table = 'called_vote'

    def __repr__(self):
        return 'CalledVote(nickname=%r, map=%r, vote_type=%r)' % (self.player, self.map, self.vote_type)


class XDFServer(BaseModel):
    name = CharField()
    admins = CharField()
    color = CharField()
    logo = TextField()
    logo_hires = TextField()
    physics = CharField(default='xdf')
    server_list_name = CharField(null=True)
    public_addr = CharField(null=True)

    @classmethod
    def get_physics_list(cls):
        return cls.select(cls.physics).distinct()


class XDFPlayer(BaseModel):
    stats_id = IntegerField(index=True, null=True)
    raw_nickname = CharField()
    nickname = CharField()
    xanmel_player = ForeignKeyField(Player, null=True)

    @classmethod
    def get_player(cls, crypto_idfp, raw_nickname, elo_request_signature):
        nickname = Color.dp_to_none(raw_nickname.encode('utf8')).decode('utf8')
        try:
            key = XDFPlayerKey.get(XDFPlayerKey.crypto_idfp == crypto_idfp)
            player = key.player
        except DoesNotExist:
            player = cls.create(raw_nickname=raw_nickname, nickname=nickname)
            key = XDFPlayerKey.create(player=player, crypto_idfp=crypto_idfp)
            xanmel_player = Player.from_cryptoidfp(crypto_idfp, elo_request_signature)
            if xanmel_player:
                player.xanmel_player = xanmel_player
                if player.stats_id is None:
                    player.stats_id = xanmel_player.stats_id
            player.save()
        return player


class XDFPlayerKey(BaseModel):
    player = ForeignKeyField(XDFPlayer)
    crypto_idfp = CharField(index=True)


class XDFTimeRecord(BaseModel):
    map = CharField(index=True)
    server = ForeignKeyField(XDFServer, related_name='time_records')
    player = ForeignKeyField(XDFPlayer)
    server_pos = IntegerField()
    server_max_pos = IntegerField(null=True)
    global_physics_pos = IntegerField(null=True)
    global_physics_max_pos = IntegerField(null=True)
    global_pos = IntegerField(null=True)
    global_max_pos = IntegerField(null=True)
    time = DecimalField(max_digits=20, decimal_places=6)
    video_url = CharField(null=True)
    timestamp = DateTimeField(default=current_time)

    @property
    def youtube_embed_code(self):
        id = self.video_url.split('/')[-1]
        return '''<iframe width="480" height="300" src="https://www.youtube.com/embed/{}" frameborder="0"
        allow="autoplay; encrypted-media" allowfullscreen> </iframe>'''.format(id)

    @classmethod
    def get_map_list(cls):
        return cls.select(cls.map).distinct()

    @classmethod
    def update_server_pos(cls, server, maps=None):
        if maps is None:
            maps = [i.map for i in cls.get_map_list()]
        for map_name in maps:
            records = cls.select().where(cls.map == map_name, cls.server == server).order_by(cls.time.asc(), cls.server_pos.asc())
            max_pos = records.count()
            for pos, i in enumerate(records, start=1):
                if i.server_pos != pos or i.server_max_pos != max_pos:
                    i.server_pos = pos
                    i.server_max_pos = max_pos
                    i.save()

    @classmethod
    def update_global_physics_pos(cls, maps=None):
        for physics in XDFServer.get_physics_list():
            servers = XDFServer.select().where(XDFServer.physics == physics.physics)
            if maps is None:
                maps = [i.map for i in cls.get_map_list()]
            for map_name in maps:
                records = cls.select().where(cls.server.in_(servers), cls.map == map_name).order_by(cls.time.asc(),
                                                                                                    cls.server_pos.asc())
                max_pos = records.count()
                for pos, i in enumerate(records, start=1):
                    if i.global_max_pos != pos or i.global_physics_max_pos != max_pos:
                        i.global_physics_pos = pos
                        i.global_physics_max_pos = max_pos
                        i.save()

    @classmethod
    def update_global_pos(cls, maps=None):
        if maps is None:
            maps = [i.map for i in cls.get_map_list()]
        for map_name in maps:
            records = cls.select().where(cls.map == map_name).order_by(cls.time.asc(), cls.server_pos.asc())
            max_pos = records.count()
            for pos, i in enumerate(records, start=1):
                if i.global_pos != pos or i.global_max_pos != max_pos:
                    i.global_pos = pos
                    i.global_max_pos = max_pos
                    i.save()

    @classmethod
    def get_record_for(cls, map, player, server):
        q = cls.select().where(cls.map == map, cls.server == server, cls.player == player).order_by(cls.server_pos)
        if q.count() > 0:
            return q[0]
        else:
            return

    @classmethod
    def get_records_for(cls, server):
        maps = defaultdict(dict)
        q = cls.select().where(cls.server == server).order_by(cls.server_pos.desc())
        for i in q:
            maps[i.map][i.player_id] = i
        return maps


class XDFSpeedRecord(BaseModel):
    map = CharField(index=True)
    server = ForeignKeyField(XDFServer)
    player = ForeignKeyField(XDFPlayer)
    speed = DecimalField(max_digits=20, decimal_places=6)
    timestamp = DateTimeField(default=current_time)


class EventType(EChoice):
    TIME_RECORD = (0, 'Time Record')
    SPEED_RECORD = (1, 'Speed Record')


class XDFNewsFeed(BaseModel):
    timestamp = DateTimeField(default=current_time)
    event_type = SmallIntegerField(choices=EventType.choices())
    time_record = ForeignKeyField(XDFTimeRecord, null=True)
    speed_record = ForeignKeyField(XDFSpeedRecord, null=True)

    @property
    def server(self):
        if self.event_type == EventType.TIME_RECORD.value:
            return self.time_record.server
        elif self.event_type == EventType.SPEED_RECORD.value:
            return self.speed_record.server

    @property
    def map(self):
        if self.event_type == EventType.TIME_RECORD.value:
            return self.time_record.map
        elif self.event_type == EventType.SPEED_RECORD.value:
            return self.speed_record.map

    @classmethod
    def filter_feed(cls):
        q = (cls.select()
             .join(XDFTimeRecord, JOIN_LEFT_OUTER, on=(cls.time_record == XDFTimeRecord.id))
             .join(XDFSpeedRecord, JOIN_LEFT_OUTER, on=(cls.speed_record == XDFSpeedRecord.id))
             .order_by(cls.timestamp.desc()))
        return q


class LadderAlgo(EChoice):
    CLASSIC = (0, 'Classic')


class LadderType(EChoice):
    GLOBAL = (0, 'Global')
    # PHYSICS = (1, 'Physics')
    SERVER = (2, 'Server')


class XDFLadder(BaseModel):
    timestamp = DateTimeField(null=True)
    algo = SmallIntegerField(choices=LadderAlgo.choices())
    type = SmallIntegerField(choices=LadderAlgo.choices())
    server = ForeignKeyField(XDFServer, null=True)
    physics = CharField(index=True, null=True)
    max_position = IntegerField(null=True)


class XDFLadderPosition(BaseModel):
    ladder = ForeignKeyField(XDFLadder)
    player = ForeignKeyField(XDFPlayer)
    points = DecimalField(max_digits=50, decimal_places=5)
    position = IntegerField(null=True)
    data = BinaryJSONField()


class PlayerAccount(BaseModel):
    player = ForeignKeyField(Player)
    balance = DecimalField(decimal_places=2, default=1000)


class AccountTransaction(BaseModel):
    account = ForeignKeyField(PlayerAccount)
    timestamp = DateField(default=current_time)
    change = DecimalField(decimal_places=2)
    description = CharField()


class IdentificationKey:
    fields = ('crypto_idfp', 'ip_address', 'raw_nickname', 'country', 'city', 'subdivisions',
              'continent', 'network_name', 'network_cidr', 'network_country_code')

    def __init__(self, identification):
        self.key = tuple([getattr(identification, i) for i in self.fields])

    def __eq__(self, other):
        if not isinstance(other, IdentificationKey):
            return False
        else:
            return self.key == other.key

    def __hash__(self):
        return hash(self.key)

    def full_geoloc(self):
        res = ''
        if self.get('country'):
            res += self.get('country')
        if self.get('subdivisions'):
            res += ', ' + self.get('subdivisions')
        if self.get('city'):
            res += ', ' + self.get('city')
        if not res:
            res = 'unknown'
        return res

    def get(self, field):
        return self.key[self.fields.index(field)]


class PlayerIdentification(BaseModel):
    server = ForeignKeyField(Server, null=True)
    player = ForeignKeyField(Player, null=True)
    crypto_idfp = CharField(index=True, null=True)
    stats_id = IntegerField(index=True, null=True)
    ip_address = CharField(index=True)
    raw_nickname = CharField()
    nickname = CharField(index=True)
    timestamp = DateTimeField(default=current_time)
    country = CharField(max_length=3, index=True, null=True)
    city = CharField(index=True, null=True)
    subdivisions = CharField(index=True, null=True)
    continent = CharField(index=True, null=True)
    latitude = FloatField(null=True, index=True)
    longitude = FloatField(null=True, index=True)
    asn = CharField(null=True, index=True)
    asn_cidr = CharField(null=True, index=True)
    asn_country_code = CharField(max_length=3, index=True, null=True)
    network_name = CharField(index=True, null=True)
    network_cidr = CharField(index=True, null=True)
    network_country_code = CharField(max_length=3, index=True, null=True)

    def to_key(self):
        return IdentificationKey(self)

    @classmethod
    def geolocate(cls, geo_response):
        if geo_response is not None:
            return {
                'country': geo_response.country.iso_code,
                'city': geo_response.city.name,
                'subdivisions': geo_response.subdivisions and ', '.join([i.name for i in geo_response.subdivisions]),
                'continent': geo_response.continent.name,
                'latitude': geo_response.location.latitude,
                'longitude': geo_response.location.longitude,
            }
        else:
            return {}

    @classmethod
    def whois(cls, whois_response):
        if whois_response is not None:
            return {
                'asn': whois_response.get('asn'),
                'asn_cidr': whois_response.get('asn_cidr'),
                'asn_country_code': whois_response.get('asn_country_code'),
                'network_name': whois_response.get('network', {}).get('name'),
                'network_cidr': whois_response.get('network', {}).get('cidr'),
                'network_country_code': whois_response.get('network', {}).get('country'),
            }
        else:
            return {}
