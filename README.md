Xanmel
------
[![Build Status](https://travis-ci.org/nsavch/xanmel.svg?branch=master)](https://travis-ci.org/nsavch/xanmel)
[![Coverage Status](https://coveralls.io/repos/github/nsavch/xanmel/badge.png?branch=master)](https://coveralls.io/github/nsavch/xanmel?branch=master)
[![Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6--dev-blue.svg)](https://img.shields.io/badge/python-3.5%2C%203.6--dev-blue.svg)

Xanmel is a modular IRC bot designed primarily for gaming.

Includes GeoLite2-City.mmdb database made by Maxmind (http://maxmind.com).


Installation
------------

  1. Install docker (https://www.docker.com/)
  2. Check out this repository
  3. Copy example_config.yaml to config.yaml (keeping it in the same directory)
  4. Edit config.yaml as per your needs
  5. Run `docker build -t xanmel .`
  6. Launch the bot by running `docker run xanmel`
