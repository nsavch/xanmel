import importlib
import inspect
import logging
import logging.config
import os
from collections import defaultdict

import sys

import copy
from pkg_resources import resource_filename, require, DistributionNotFound

import click
import geoip2.database
import asyncio
import uvloop

import time
import yaml

from .db import XanmelDB
from .utils import current_time
from .logcfg import logging_config

logger = logging.getLogger(__name__)


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class Xanmel:
    """
    The basic metadata holder. There should be only 1 instance per running process of this class.
    """

    def __init__(self, loop, config_path):
        self.modules = {}
        self.handlers = defaultdict(list)
        self.actions = {}
        self.loop = loop
        # TODO: handle situation when geoip db isn't readable
        self.geoip = geoip2.database.Reader(resource_filename('xanmel', 'GeoLite2-City.mmdb'))
        self.cmd_root = CommandRoot(self)
        self.cmd_root.register_container(HelpCommands(), prefix='')
        try:
            with open(os.path.expanduser(config_path), 'r') as config_file:
                self.config = yaml.safe_load(config_file)
        except (OSError, IOError) as e:
            print('Config file %s unreadable: %s' % (config_path, e))
            sys.exit(1)
        logging.config.dictConfig(logging_config(self.config['settings'].get('log_level', 'INFO')))
        logger.info('Read configuration from %s', config_path)
        loop.set_debug(self.config['settings']['asyncio_debug'])
        self.db = XanmelDB(self.config['settings'].get('db_url'))

    def load_modules(self):
        for module_path, module_config in self.config['modules'].items():
            module_pkg_name, module_name = module_path.rsplit('.', 1)
            module_pkg = importlib.import_module(module_pkg_name)
            module = getattr(module_pkg, module_name)(self, module_config)
            self.modules[module_path] = module
            self.load_handlers(module, module_pkg_name)
            self.load_actions(module, module_pkg_name)
            self.setup_event_generators(module)
            self.db.create_tables(module_pkg_name)
        self.run_after_load_hooks()

    def load_handlers(self, module, module_pkg_name):
        try:
            handlers_mod = importlib.import_module(module_pkg_name + '.handlers')
        except ImportError:
            logger.debug('No handlers in module %s', module_pkg_name)
            return
        for _, member in inspect.getmembers(handlers_mod, inspect.isclass):
            if issubclass(member, Handler):
                handler = member(module=module)
                for event in handler.events:
                    self.handlers[event].append(handler)

    def load_actions(self, module, module_pkg_name):
        try:
            actions_mod = importlib.import_module(module_pkg_name + '.actions')
        except ImportError:
            logger.debug('No actions in module %s', module_pkg_name)
            return
        for _, member in inspect.getmembers(actions_mod, inspect.isclass):
            if issubclass(member, Action):
                action = member(module=module)
                self.actions[member] = action

    def setup_event_generators(self, module):
        module.setup_event_generators()

    def run_after_load_hooks(self):
        for i in self.modules.values():
            i.after_load()

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

    def after_load(self):
        pass

    def setup_event_generators(self):
        pass  # pragma: no cover

    def teardown(self):
        pass  # pragma: no cover


class Event:
    log = True

    def __init__(self, module, **kwargs):
        self.module = module
        self.properties = kwargs
        self.timestamp = current_time()

    def fire(self):
        if self.log:
            logger.info(str(self))
        else:
            logger.debug(str(self))
        for i in self.module.xanmel.handlers[type(self)]:
            self.module.loop.create_task(i.handle(self))

    def __str__(self):
        return '%s(%r)' % (type(self).__name__, self.properties)


class Action:
    # TODO: include list of required/optional properties
    def __init__(self, module):
        self.module = module

    async def run(self, **kwargs):
        raise NotImplementedError()  # pragma: no cover


class Handler:
    events = []

    def __init__(self, module):
        self.module = module

    async def run_action(self, action, **kwargs):
        action = self.module.xanmel.actions[action]
        await action.run(**kwargs)

    async def handle(self, event):
        pass  # pragma: no cover


class ChatConfirmations:
    def __init__(self):
        self.confirmations = {}

    def reset(self):
        self.confirmations = {}

    def __contains__(self, item):
        return item in self.confirmations

    def __getitem__(self, item):
        return self.confirmations[item]

    def __delitem__(self, key):
        del self.confirmations[key]

    async def ask(self, user, prompt, yes_cb, no_cb, is_private=False):
        self.confirmations[user.unique_id()] = (yes_cb, no_cb)
        await user.reply('{} /yes or /no'.format(prompt), is_private)


class ChatUser:
    user_type = ''

    def __init__(self, module, name, **kwargs):
        self.module = module
        self.name = name
        self.properties = kwargs

    def unique_id(self):
        raise NotImplementedError  # pragma: no cover

    @property
    def is_admin(self):
        return False  # pragma: no cover

    async def reply(self, message, is_private, **kwargs):
        if is_private:
            await self.private_reply(message, **kwargs)
        else:
            await self.public_reply(message, **kwargs)

    async def private_reply(self, message, **kwargs):
        pass  # pragma: no cover

    async def public_reply(self, message, **kwargs):
        pass  # pragma: no cover


class CommandRoot:
    def __init__(self, xanmel):
        self.xanmel = xanmel
        self.children = {}
        self.merged_containers = []
        self.throttling = defaultdict(lambda: defaultdict(list))
        self.disabled_users = defaultdict(dict)

    def copy(self):
        new_root = CommandRoot(self.xanmel)
        new_root.children = copy.copy(self.children)
        new_root.merged_containers = copy.copy(self.merged_containers)
        return new_root

    def register_container(self, container, prefix):
        container.root = self
        container.prefix = prefix
        if not prefix:
            self.merged_containers.append(container)
            for i in container.children.values():
                if i.prefix not in self.children:
                    self.children[i.prefix] = i
                else:
                    logger.info('Prefix %s already registered. Skipping command %s', i.prefix, i)
        else:
            if prefix not in self.children:
                self.children[prefix] = container
            else:
                logger.info('Prefix %s already registered. Skipping command container %s', prefix, container)

    async def run(self, user, message, is_private=False):
        print(self.children)
        ut = user.user_type
        uid = user.unique_id()
        logger.debug('Running a command for user %s, message %s', uid, message)

        if uid in self.disabled_users[ut]:
            if time.time() - self.disabled_users[ut][uid] > 60:
                del self.disabled_users[ut][uid]
            else:
                logger.info('User %s:%s throttled for flooding!', ut, uid)
                return
        self.throttling[ut][uid].append(time.time())
        while time.time() - self.throttling[ut][uid][0] > 10:
            self.throttling[ut][uid].pop(0)
        if len(self.throttling[ut][uid]) > 5:
            logger.info('User %s:%s throttled for flooding!', ut, uid)
            self.disabled_users[ut][uid] = time.time()
            return

        message = message.lstrip()
        prefix = message.split(' ', 1)[0]
        if prefix not in self.children:
            if is_private:
                reply = 'Unknown command. Use "help" to list available commands'
            else:
                reply = 'Unknown command. Use "%s: help" to list available commands' % user.botnick
            await user.reply(reply, is_private)
        else:
            child = self.children[prefix]
            if child.is_allowed_for(user):
                await child.run(user, message[len(prefix):], is_private, root=self)
            else:
                await user.reply('Access Denied', is_private)


class CommandContainer:
    root = None
    children_classes = None
    prefix = ''
    properties = None
    help_text = ''
    include_confirmations = False

    def __init__(self, **kwargs):
        self.properties = kwargs
        self.children = {}
        self.confirmations = ChatConfirmations()
        if self.include_confirmations:
            yes_command = Yes()
            no_command = No()
            yes_command.parent = self
            no_command.parent = self
            self.children[yes_command.prefix] = yes_command
            self.children[no_command.prefix] = no_command

        if not self.children_classes:
            return
        for k, v in self.children_classes.items():
            self.children[k] = v()
            self.children[k].parent = self

    def is_allowed_for(self, user):
        return not self.children or any([i.is_allowed_for(user) for i in self.children.values()])

    async def run(self, user, message, is_private=False, root=None):
        message = message.lstrip()
        if not self.children:
            logger.info('Request to a container without children %s', self)
            return
        if not message:
            reply = '%(prefix)s: %(help)s. Use "help %(prefix)s" to list available subcommands' % {
                'prefix': self.prefix,
                'help': self.help_text
            }
            await user.reply(reply, is_private)
            return
        prefix = message.split(' ', 1)[0]
        if prefix not in self.children:
            if is_private:
                reply = 'Unknown command %s %s. Use "help %s" to list available commands' % \
                        (self.prefix, prefix, self.prefix)
            else:
                reply = 'Unknown command %s %s. Use "%s: help %s" to list available commands' % \
                        (self.prefix, prefix, user.botnick, self.prefix)
            await user.reply(reply, is_private)
        else:
            child = self.children[prefix]

            if child.is_allowed_for(user):
                await child.run(user, message[len(prefix):], is_private, root=root)
            else:
                await user.reply('Access Denied', is_private)


class ConnectChildrenMeta(type):
    def __new__(mcs, name, bases, namespace, **kwds):
        instance = type.__new__(mcs, name, bases, dict(namespace))
        if namespace.get('parent'):
            if namespace['parent'].children_classes is None:
                namespace['parent'].children_classes = {}
            if not instance.prefix:
                logger.info('Skipping registering command %s: empty prefix', instance)
            elif instance.prefix in namespace['parent'].children_classes:
                logger.info('Skipping registering command %s: prefix already registered', instance)
            else:
                namespace['parent'].children_classes[instance.prefix] = instance
        return instance


class ChatCommand(metaclass=ConnectChildrenMeta):
    parent = None
    prefix = ''
    help_args = ''
    help_text = ''
    allowed_user_types = '__all__'
    disallowed_user_types = []
    admin_required = False

    def is_allowed_for(self, user):
        allowed = True
        if self.allowed_user_types != '__all__':
            allowed = user.user_type in self.allowed_user_types
        if allowed:
            allowed = user.user_type not in self.disallowed_user_types
        if self.admin_required and not user.is_admin:
            allowed = False
        return allowed

    def format_help(self):
        if self.help_args:
            return '%s %s: %s' % (self.prefix, self.help_args, self.help_text)
        else:
            return '%s: %s' % (self.prefix, self.help_text)

    async def run(self, user, message, is_private=False):
        raise NotImplementedError  # pragma: no cover


class Yes(ChatCommand):
    parent = None
    prefix = 'yes'
    help_args = ''
    help_text = 'Confirm an action (you should be prompted before you use this command)'

    async def run(self, user, message, is_private=False, root=None):
        if user.unique_id() not in self.parent.confirmations:
            await user.reply('We didn\'t ask you anything.', is_private=True)
        else:
            await self.parent.confirmations[user.unique_id()][0]()
            del self.parent.confirmations[user.unique_id()]


class No(ChatCommand):
    parent = None
    prefix = 'no'
    help_args = ''
    help_text = 'Decline an action (you should be prompted before you use this command)'

    async def run(self, user, message, is_private=False, root=None):
        if user.unique_id() not in self.parent.confirmations:
            await user.reply('We didn\'t ask you anything.', is_private=True)
        else:
            await self.parent.confirmations[user.unique_id()][1]()
            del self.parent.confirmations[user.unique_id()]


class HelpCommands(CommandContainer):
    help_text = 'Commands for getting help'


class Help(ChatCommand):
    parent = HelpCommands
    prefix = 'help'
    help_args = '[CMDNAME] [SUBCMDNAME]'
    help_text = 'Provide useful and friendly help.'

    async def run(self, user, message, is_private=False, root=None):
        if is_private:
            help_base = 'help'
        else:
            help_base = '%s: help' % user.botnick
        message = message.strip()
        if message:
            prefix = message.split(' ', 1)[0]
            if prefix not in root.children:
                reply = ['Unknown command %s. Use "%s" to list available commands' % (prefix, help_base)]
            else:
                child = root.children[prefix]
                if isinstance(child, CommandContainer):
                    rest = message[len(prefix):].strip()
                    if not rest:
                        cmds = child.children
                        reply = ['%s: %s' % (prefix, child.help_text),
                                 'Available commands: ' + ', '.join(
                                     sorted([i for i in cmds if cmds[i].is_allowed_for(user)]))]
                    else:
                        child_prefix = rest.split(' ', 1)[0]
                        if child_prefix not in child.children:
                            reply = [
                                'Unknown command %(prefix)s %(child_prefix)s. Use "%(help_base)s %(prefix)s" to list '
                                'available commands' % {
                                    'prefix': prefix,
                                    'child_prefix': child_prefix,
                                    'help_base': help_base
                                }
                            ]
                        else:
                            cmd = child.children[child_prefix]
                            if cmd.is_allowed_for(user):
                                reply = ['%s %s' % (prefix, cmd.format_help())]
                            else:
                                reply = ['Unavailable command %s %s' % (prefix, child_prefix)]
                else:
                    if child.is_allowed_for(user):
                        reply = [child.format_help()]
                    else:
                        reply = ['Unavailable command %s' % prefix]
        else:
            cmds = root.children
            reply = ['Available commands: ' + ', '.join(sorted([i for i in cmds if cmds[i].is_allowed_for(user)]))]
        for i in reply:
            await user.reply(i, is_private)


class FullHelp(ChatCommand):
    parent = HelpCommands
    prefix = 'fullhelp'
    help_text = 'Send a documentation for all commands in a private message'

    async def run(self, user, message, is_private=False, root=None):
        reply = ['Angle brackets designate <required> command parameters.',
                 'Square brackets designate [optional] command parameters']
        for i in root.merged_containers:
            if i.is_allowed_for(user):
                reply.append('-- ' + i.help_text + ' --')
                for child_prefix in sorted(i.children):
                    if child_prefix in root.children:
                        if root.children[child_prefix].is_allowed_for(user):
                            reply.append(root.children[child_prefix].format_help())
        for child_prefix in sorted(root.children):
            child = root.children[child_prefix]
            if not isinstance(child, CommandContainer):
                continue
            if child.is_allowed_for(user):
                reply.append('-- %s: %s --' % (child_prefix, child.help_text))
                for subchild_prefix in sorted(child.children):
                    if child.children[subchild_prefix].is_allowed_for(user):
                        reply.append('%s %s' % (child_prefix, child.children[subchild_prefix].format_help()))
        for i in reply:
            await asyncio.sleep(1)  # Sleep 1 second to prevent kicking for Excess Flood
            await user.private_reply(i)


class Version(ChatCommand):
    parent = HelpCommands
    prefix = 'version'
    help_text = 'Get the current version of the bot running'

    async def run(self, user, message, is_private=False, root=None):
        try:
            version = require('xanmel')[0].version
        except DistributionNotFound:
            version = 'Unknown version (please install xanmel using setuptools)'
        await user.reply(version, is_private=is_private)


@click.command()
@click.option('-c', '--config', default=None, help='Path to config file', metavar='CONFIG')
def main(config):
    if config is None:
        tried = []
        for i in ['/etc/', os.getcwd()]:
            fn = os.path.join(i, 'xanmel.yaml')
            tried.append(fn)
            if os.path.isfile(fn):
                config = fn
                break
        if config is None:
            print('Could not find config file. Tried the following paths: %s' % ', '.join(tried))
            return 1
    loop = asyncio.get_event_loop()
    xanmel = Xanmel(loop=loop, config_path=config)
    logger.info('Starting event loop...')

    xanmel.load_modules()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        loop.close()
    return 0
