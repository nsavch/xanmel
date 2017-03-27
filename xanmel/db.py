import importlib
import inspect
import logging

import peewee
import peewee_async
from playhouse.db_url import connect, register_database


register_database(peewee_async.PostgresqlDatabase, 'postgres')
register_database(peewee_async.PooledPostgresqlDatabase, 'postgres+pool')
register_database(peewee_async.PostgresqlDatabase, 'postgresql')
register_database(peewee_async.PooledPostgresqlDatabase, 'postgresql+pool')


logger = logging.getLogger(__name__)

database_proxy = peewee.Proxy()


class BaseModel(peewee.Model):
    class Meta:
        database = database_proxy


class XanmelDB:
    def __init__(self, db_url):
        if db_url:
            self.db = connect(db_url)
            self.mgr = peewee_async.Manager(database_proxy)
            database_proxy.initialize(self.db)
        else:
            self.db = None

    def create_tables(self, module_pkg_name):
        if not self.is_up:
            return
        try:
            models = importlib.import_module(module_pkg_name + '.models')
        except ImportError:
            return
        for model_name, model in inspect.getmembers(models, inspect.isclass):
            if issubclass(model, BaseModel) and model is not BaseModel:
                logger.debug('Creating table for model %s', model_name)
                self.db.create_table(model, safe=True)

    @property
    def is_up(self):
        return self.db is not None
