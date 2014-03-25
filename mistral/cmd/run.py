#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import sys
import eventlet
eventlet.monkey_patch(
        os=True,
        select=True,
        socket=True,
        thread=False if '--use-debugger' in sys.argv else True,
        time=True)

import os
import threading

# If ../mistral/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'mistral', '__init__.py')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from oslo import messaging
from oslo.config import cfg

from mistral import config
from mistral.engine.fake import engine
from mistral.engine.fake import proxy

from mistral.api import app
from wsgiref import simple_server

from mistral.openstack.common import log as logging


LOG = logging.getLogger(__name__)

def launch_engine_pool(transport):
    try:
        target = messaging.Target(topic="executor",
                                  server="0.0.0.0")
        endpoints = [engine.EnginePool()]
        engine_server = messaging.get_rpc_server(transport, target, endpoints)
        engine_server.start()
        engine_server.wait()
    except RuntimeError, e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)


def launch_api(transport):
    try:
        host = cfg.CONF.api.host
        port = cfg.CONF.api.port
        server = simple_server.make_server(
                    host, port, app.setup_app(transport=transport))
        LOG.info("Mistral API is serving on http://%s:%s (PID=%s)" %
                 (host, port, os.getpid()))
        server.serve_forever()
    except RuntimeError, e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)


def main():
    try:
        config.parse_args()
        logging.setup('Mistral')

        transport = proxy.get_transport()

        # launch the servers on different threads
        t_eng = threading.Thread(target=launch_engine_pool, args=(transport,))
        t_api = threading.Thread(target=launch_api, args=(transport,))
        t_eng.start()
        t_api.start()
        t_api.join()
    except RuntimeError, e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)


if __name__ == '__main__':
    main()
