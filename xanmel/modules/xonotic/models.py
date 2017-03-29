from peewee import *

from xanmel import current_time
from xanmel.db import BaseModel


class MapRating(BaseModel):
    map = CharField(index=True)
    nickname = CharField(index=True)
    raw_nickname = CharField()
    server_id = IntegerField(index=True)
    stats_id = IntegerField(index=True, null=True)
    timestamp = DateTimeField(default=current_time)
    vote = IntegerField()
    message = CharField()

    class Meta:
        db_table = 'map_rating'

    def __repr__(self):
        return 'MapRating(nicname=%r, map=%r, vote=%r)' % (self.nickname, self.map, self.vote)


class CalledVote(BaseModel):
    map = CharField(index=True)
    nickname = CharField(index=True)
    raw_nickname = CharField()
    server_id = IntegerField(index=True)
    stats_id = IntegerField(index=True, null=True)
    timestamp = DateTimeField(default=current_time)
    vote_type = CharField(index=True)
    time_since_round_start = IntegerField()

    class Meta:
        db_table = 'called_vote'

    def __repr__(self):
        return 'CalledVote(nicname=%r, map=%r, vote_type=%r)' % (self.nickname, self.map, self.vote)
