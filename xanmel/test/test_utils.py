from xanmel.utils import *


def test_current_time():
    time = current_time()
    assert time.tzinfo == pytz.timezone('UTC')
