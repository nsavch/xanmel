from setuptools import setup, find_packages


setup(
    name='xanmel',
    version='0.2a1',
    description='Extensible chatbot designed for gaming purposes',
    long_description='TODO',
    url='https://gitlab.com/nsavch/xanmel',
    author='Nick Savchenko',
    author_email='nsavch@gmail.com',
    license='GPLv3',
    packages=find_packages(exclude=['xanmel.test', 'xanmel.modules.*.test']),
    package_data={
        'xanmel': ['GeoLite2-City.mmdb'],
    },
    keywords='xonotic irc chatbot',
    install_requires=[
        'setuptools',
        'aiodns==1.1.1',
        'aiohttp==1.3.3',
        'bottom==1.1.0',
        'cchardet==1.1.3',
        'geoip2==2.4.2',
        'maxminddb==1.2.3',
        'pytz==2016.10',
        'PyYAML==3.12',
        'aiopg==0.13.0',
        'peewee==2.9.1',
        'peewee-async==0.5.7',
        'psycopg2==2.7.1'
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
    ],
    entry_points={
        'console_scripts': [
            'xanmel=xanmel:main'
        ]
    }

)
