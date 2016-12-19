import asyncio
import asynctest

import pytest
import random

from xanmel import Xanmel, ChatUser


@pytest.fixture()
def dummy_chat_user():
    class DummyChatUser(ChatUser):
        def __init__(self, module, name, **kwargs):
            super(DummyChatUser, self).__init__(module, name, **kwargs)
            self.dummy_admin = True
            self.uid = random.randint(0, 1024*1024)

        def unique_id(self):
            return self.uid

        @property
        def is_admin(self):
            return self.dummy_admin

        private_reply = asynctest.CoroutineMock()
        public_reply = asynctest.CoroutineMock()

    return DummyChatUser


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def irc_module(xanmel):
    return xanmel.modules['xanmel.modules.irc.IRCModule']


@pytest.fixture
def xon_module(xanmel):
    return xanmel.modules['xanmel.modules.xonotic.XonoticModule']


@pytest.fixture
def xanmel(event_loop, mocker):
    xanmel = Xanmel(event_loop, 'example_config.yaml')
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    return xanmel


@pytest.fixture
def mocked_coro():
    return asynctest.CoroutineMock()
