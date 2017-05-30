Xanmel
------
[![Build Status](https://travis-ci.org/nsavch/xanmel.svg?branch=master)](https://travis-ci.org/nsavch/xanmel)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/3d0ba1bff5154dbd8c65b28d5a7b94ca)](https://www.codacy.com/app/nsavch/xanmel?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=nsavch/xanmel&amp;utm_campaign=Badge_Grade)
[![Coverage Status](https://coveralls.io/repos/github/nsavch/xanmel/badge.svg?branch=master)](https://coveralls.io/github/nsavch/xanmel?branch=master)
[![Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7--dev-blue.svg)](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7--dev-blue.svg)
[![Updates](https://pyup.io/repos/github/nsavch/xanmel/shield.svg)](https://pyup.io/repos/github/nsavch/xanmel/)
[![Python 3](https://pyup.io/repos/github/nsavch/xanmel/python-3-shield.svg)](https://pyup.io/repos/github/nsavch/xanmel/)


Xanmel is a modular IRC bot designed primarily for gaming.

Includes GeoLite2-City.mmdb database made by Maxmind (http://maxmind.com).


Installation (for production)
------------

  1. Install python (3.5 or later)
  2. Clone the repo, cd to workdir and run `python3 setup.py install`
  3. run `xanmel --config /path/to/xanmel.yaml`
 
 
 Installation (for development)
 ------------
 
  1. Install python (3.5 or later)
  2. Clone the repo
  3. Create a virtual environment `virtualenv /path/to/venv`
  4. `source /path/to/venv/bin/activate`
  5. cd to the repo workdir
  6. `pip install -r requirements.txt`
  7. `python run.py`
