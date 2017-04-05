from peewee import *

from xanmel import current_time
from xanmel.db import BaseModel


class Server(BaseModel):
    name = CharField(null=True)
    config_name = CharField()


class Player(BaseModel):
    crypto_idfp = CharField(index=True, null=True)
    stats_id = IntegerField(index=True, null=True)
    raw_nickname = CharField()
    nickname = CharField()


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
        return 'MapRating(nicname=%r, map=%r, vote=%r)' % (self.player, self.map, self.vote)


class CalledVote(BaseModel):
    map = ForeignKeyField(Map)
    player = ForeignKeyField(Player)
    timestamp = DateTimeField(default=current_time)
    vote_type = CharField(index=True)
    time_since_round_start = IntegerField()

    class Meta:
        db_table = 'called_vote'

    def __repr__(self):
        return 'CalledVote(nicname=%r, map=%r, vote_type=%r)' % (self.player, self.map, self.vote_type)


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
