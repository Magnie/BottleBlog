# The core of the web server.

from bottle import default_app, run
import bottle
from paste import httpserver


from blog import *  # The Bottle Blog App

HOST = '0.0.0.0'
PORT = 8081

bottle.debug(True)
run(reloader=True, port=PORT)

httpserver.serve(default_app(), host=HOST, port=PORT)