import http.client
from urllib.parse import quote

from peewee import *

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


class XDFTimeRecord(BaseModel):
    map = ForeignKeyField(Map)
    player = ForeignKeyField(Player)
    position = IntegerField()
    time = IntegerField()
    timestamp = DateTimeField(default=current_time)


class XDFSpeedRecord(BaseModel):
    map = ForeignKeyField(Map)
    player = ForeignKeyField(Player)
    speed = FloatField()
    timestamp = DateTimeField(default=current_time)


class PlayerAccount(BaseModel):
    player = ForeignKeyField(Player)
    balance = DecimalField(decimal_places=2, default=1000)


class AccountTransaction(BaseModel):
    account = ForeignKeyField(PlayerAccount)
    timestamp = DateField(default=current_time)
    change = DecimalField(decimal_places=2)
    description = CharField()


class PlayerIdentification(BaseModel):
    server = ForeignKeyField(Server, null=True)
    player = ForeignKeyField(Player, null=True)
    crypto_idfp = CharField(index=True, null=True)
    stats_id = IntegerField(index=True, null=True)
    ip_address = CharField(index=True)
    raw_nickname = CharField()
    nickname = CharField()
    timestamp = DateTimeField(default=current_time)
    country = CharField(max_length=3, index=True, null=True)
    city = CharField(index=True, null=True)
    subdivisions = CharField(index=True, null=True)
    continent = CharField(index=True, null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)

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
