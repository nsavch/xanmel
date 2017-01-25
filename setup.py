from setuptools import setup, find_packages


setup(
    name='xanmel',
    version='0.1a1',
    description='Extensible chatbot designed for gaming purposes',
    url='https://gitlab.com/nsavch/xanmel',
    author='Nick Savchenko',
    author_email='nsavch@gmail.com',
    license='GPLv3',
    packages=find_packages(exclude=['xanmel.test', 'xanmel.modules.*.test']),
    install_requires=[
        'aiohttp==1.0.5',
        'bottom==1.0.4',
        'pytz==2016.10',
        'maxminddb==1.2.2',
        'geoip2==2.4.2',
        'PyYAML==3.12',

    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',  # gamers
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Topic :: Games/Entertainment',
    ]

)
