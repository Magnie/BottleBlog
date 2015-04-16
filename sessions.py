# -*- coding: utf-8 -*-

# The unofficial Sessions addon for Bottle (bottlepy.org)
# Made by Magnie (magnie.tk) and Ohaider (fallingduck.tk)
# License: MIT

from random import randint
from time import time
from hashlib import new
from bottle import request, response

class Session(object):
    def __init__(self):
        self.data = {}
    def start(self):
        if not(request.get_cookie('PYSESSID')):
            sid = new('sha1', str(int(time() * 1000)) + str(randint(0, 4596))).hexdigest()
            self.data[sid] = {}
            response.set_cookie('PYSESSID', sid)
        if not(self.data.has_key(request.get_cookie('PYSESSID'))):
            self.data[request.get_cookie('PYSESSID')] = {}
    def set(self, n, v):
        try:
            sid = request.get_cookie('PYSESSID')
            self.data[sid][n] = v
        except KeyError:
            pass
    def get(self, n):
        sid = request.get_cookie('PYSESSID')
        try:
            return self.data[sid][n]
        except KeyError:
            return None

    def self_destruct(self):
        sid = request.get_cookie('PYSESSID')
        del self.data[sid]