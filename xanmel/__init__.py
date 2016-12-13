import importlib
import inspect
import logging
import os
from collections import defaultdict

import geoip2.database
import asyncio
import yaml

from xanmel.utils import current_time

logger = logging.getLogger(__name__)


class Xanmel:
    """
    The basic metadata holder. There should be only 1 instance per running process of this class.
    """
    modules = {}
    handlers = defaultdict(list)
    actions = {}

    def __init__(self, loop, config_path):
        self.loop = loop
        self.geoip = geoip2.database.Reader('GeoLite2-City.mmdb')
        self.cmd_root = CommandRoot(self)
        with open(os.path.expanduser(config_path), 'r') as config_file:
            self.config = yaml.load(config_file)

    def load_modules(self):
        for module_path, module_config in self.config.items():
            module_pkg_name, module_name = module_path.rsplit('.', 1)
            module_pkg = importlib.import_module(module_pkg_name)
            module = getattr(module_pkg, module_name)(self, module_config)
            self.modules[module_path] = module
            self.load_handlers(module, module_pkg_name)
            self.load_actions(module, module_pkg_name)
            self.setup_event_generators(module)

    def load_handlers(self, module, module_pkg_name):
        try:
            handlers_mod = importlib.import_module(module_pkg_name + '.handlers')
        except ImportError:
            logger.debug('No handlers in module %s', module_pkg_name)
            return
        for member_name, member in inspect.getmembers(handlers_mod, inspect.isclass):
            if issubclass(member, Handler):
                handler = member(module=module)
                for event in handler.events:
                    self.handlers[event].append(handler)

    def load_actions(self, module, module_pkg_name):
        try:
            actions_mod = importlib.import_module(module_pkg_name + '.actions')
        except ImportError:
            logger.debug('No handlers in module %s', module_pkg_name)
            return
        for member_name, member in inspect.getmembers(actions_mod, inspect.isclass):
            if issubclass(member, Action):
                action = member(module=module)
                self.actions[member] = action

    def setup_event_generators(self, module):
        module.setup_event_generators()

    def teardown(self):
        for i in self.modules.values():
            i.teardown()
        for task in asyncio.Task.all_tasks():
            task.cancel()


class Module:
    """
    Class representing Xanmel module. Modules are used to group functionality into different packages.

    Each xanmel module may provide the following facilities:

      * event types
      * event generators - functions which listen to the outside world and generate corresponding xanmel events
      * actions - function which alters the outside world
      * handler - function which is called when an event occur and may call zero or more actions

    Each module has its own config section.
    """

    def __init__(self, xanmel, config):
        self.config = config
        self.xanmel = xanmel
        self.loop = xanmel.loop

    def setup_event_generators(self):
        pass

    def teardown(self):
        pass


class GetNameMixin:
    @classmethod
    def get_name(cls):
        return '%s.%s' % (inspect.getmodule(cls).__name__, cls.__name__)


class Event(GetNameMixin):
    def __init__(self, module, **kwargs):
        self.module = module
        self.properties = kwargs
        self.timestamp = current_time()

    def fire(self):
        logger.info('Firing event %s', self)
        for i in self.module.xanmel.handlers[type(self)]:
            self.module.loop.create_task(i.handle(self))

    def __str__(self):
        return '%s(%r)' % (self.get_name(), self.properties)


class Action(GetNameMixin):
    # TODO: include list of required/optional properties
    def __init__(self, module):
        self.module = module

    async def run(self, **kwargs):
        raise NotImplementedError()


class Handler(GetNameMixin):
    events = []

    def __init__(self, module):
        self.module = module

    async def run_action(self, action, **kwargs):
        action = self.module.xanmel.actions[action]
        await action.run(**kwargs)

    async def handle(self, event):
        pass

    def __str__(self):
        return self.get_name()


class ChatUser:
    def __init__(self, module, name, **kwargs):
        self.module = module
        self.name = name
        self.properties = kwargs

    @property
    def is_admin(self):
        return False

    async def reply(self, message, is_private, **kwargs):
        if is_private:
            await self.private_reply(message, **kwargs)
        else:
            await self.public_reply(message, **kwargs)

    async def private_reply(self, message, **kwargs):
        pass

    async def public_reply(self, message, **kwargs):
        pass


class CommandRoot:

    def __init__(self, xanmel):
        self.xanmel = xanmel
        self.children = {}

    def register_container(self, container, prefix):
        if not prefix:
            for i in container.children.values():
                if i.prefix not in self.children:
                    self.children[i.prefix] = i
                else:
                    logger.info('Prefix %s already registered. Skipping command %s', i.prefix, i)
        else:
            if prefix not in self.children:
                container.root = self
                container.prefix = prefix
                self.children[prefix] = container
            else:
                logger.info('Prefix %s already registered. Skipping command container %s', prefix, container)

    async def run(self, user, message, is_private=False):
        message = message.lstrip()
        prefix = message.split(' ', 1)[0]
        if prefix not in self.children:
            await user.reply('Unknown command. Use "%s: help" to list available commands' % user.botnick, is_private)
        else:
            child = self.children[prefix]
            await child.run(user, message[len(prefix):], is_private)


class CommandContainer:
    root = None
    children = {}
    prefix = ''

    def __init__(self, **kwargs):
        self.properties = kwargs

    async def run(self, user, message, is_private=False):
        message = message.lstrip()
        if not self.children:
            logger.info('Request to a container without children %s', self)
            return
        prefix = message.lstrip().split(' ', 1)[0]
        if prefix not in self.children:
            await user.reply('Unknown command %s %s. Use "%s: help %s" to list available commands' %
                             (self.prefix, message, user.botnick, self.prefix), is_private)
        else:
            child = self.children[prefix]
            await child.run(user, message[len(prefix)], is_private)


class ConnectChildrenMeta(type):
    def __new__(typ, name, bases, namespace, **kwds):
        instance = type.__new__(typ, name, bases, dict(namespace))
        if namespace['parent']:
            if not instance.prefix:
                logger.info('Skipping registering command %s: empty prefix', instance)
            elif instance.prefix in namespace['parent'].children:
                logger.info('Skipping registering command %s: prefix already registered', instance)
            else:
                namespace['parent'].children[instance.prefix] = instance()
        return instance


class ChatCommand(metaclass=ConnectChildrenMeta):
    parent = None
    prefix = ''
    help_text = ''

    async def run(self, user, message, is_private=False):
        await user.reply('Command "%s" not implemented' % message, is_private)
