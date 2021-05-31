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
        'aiohttp==3.7.4',
        'bottom==2.1.3',
        'cchardet==2.1.7',
        'geoip2==2.5.0',
        'inflection==0.3.1',
        'maxminddb==2.0.3',
        'pytz==2017.2',
        'PyYAML==5.4.1',
        'aiopg==1.2.1',
        'peewee==3.14.4',
        'peewee-async==0.7.1',
        'psycopg2==2.8.6',
        'ipwhois==1.0.0',
        'uvloop==0.15.2',
        'click==6.7',
        'aio_dprcon>=0.1.6',
        'django-echoices'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',  # gamers
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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
