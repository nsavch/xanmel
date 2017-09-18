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
        'aiohttp==2.2.5',
        'bottom==2.1.1',
        'cchardet==2.1.1',
        'geoip2==2.5.0',
        'inflection==0.3.1',
        'maxminddb==1.3.0',
        'pytz==2017.2',
        'PyYAML==3.12',
        'aiopg==0.13.1',
        'peewee==2.10.1',
        'peewee-async==0.5.7',
        'psycopg2==2.7.3.1',
        'ipwhois==1.0.0',
        'uvloop==0.8.0',
        'click==6.7'
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
