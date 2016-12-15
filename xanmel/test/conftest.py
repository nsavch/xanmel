import asyncio
from unittest.mock import Mock

import pytest
import yaml
import random

from xanmel import Xanmel, ChatUser


@pytest.fixture()
def dummy_chat_user():
    class DummyChatUser(ChatUser):
        def __init__(self, module, name, **kwargs):
            super(DummyChatUser, self).__init__(module, name, **kwargs)
            self.dummy_admin = True

        def unique_id(self):
            return random.randint(0, 1024*1024)

        @property
        def is_admin(self):
            return self.dummy_admin

    return DummyChatUser


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def transport():
    class Transport:
        def __init__(self):
            self.written = []
            self.closed = False

        def write(self, data):
            self.written.append(data)

        def close(self):
            self.closed = True
    return Transport()


@pytest.fixture
def xanmel(event_loop, mocker):
    xanmel = Xanmel(event_loop, 'example_config.yaml')
    yield xanmel


@pytest.fixture
def config():
    with open('example_config.yaml') as f:
        return yaml.load(f)


@pytest.fixture
def mocked_coroutine():
    async def dummy(*args, **kwargs):
        pass
    return Mock(wraps=dummy)
