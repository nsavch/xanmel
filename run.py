import asyncio
import logging.config
import warnings

from xanmel import Xanmel

warnings.simplefilter('default')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    logger.info('Starting event loop...')
    xanmel = Xanmel(loop=loop, config_path='/etc/xanmel_config.yaml')
    xanmel.load_modules()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        loop.close()


if __name__ == '__main__':
    main()