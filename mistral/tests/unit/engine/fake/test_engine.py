import time
import eventlet
eventlet.monkey_patch()

from oslo import messaging
from oslo.config import cfg

from mistral.tests import base
from mistral.engine.fake import engine
from mistral.engine.fake import proxy

class FakeEngineTest(base.BaseTest):
    def test_fake_engine(self):
        engine_pool = engine.EnginePool()
        id1 = engine_pool.submit(ctx=None)
        id2 = engine_pool.submit(ctx=None)
        self.assertEqual(len(engine_pool.engines), 2)

        engine1 = engine_pool.get(None, id1)
        engine2 = engine_pool.get(None, id2)
        self.assertIsInstance(engine1, engine.Engine)
        self.assertIsInstance(engine2, engine.Engine)

        while engine1.status != 'STOPPED':
            time.sleep(0.1)
            engine1.stop()

    def _get_transport(self):
        #HACK: Get transport manually, bypassing mistral.config in nosetests
        from stevedore import driver
        from oslo.messaging import transport
        # Get transport here to let oslo.messaging setup default config before
        # changing the rpc_backend to the fake driver; otherwise,
        # oslo.messaging will throw exception.
        messaging.get_transport(cfg.CONF)
        cfg.CONF.set_default('rpc_backend', 'fake')
        url = transport.TransportURL.parse(cfg.CONF, None, None)
        kwargs = dict(default_exchange=cfg.CONF.control_exchange,
                      allowed_remote_exmods=[])
        mgr = driver.DriverManager('oslo.messaging.drivers',
                                   url.transport,
                                   invoke_on_load=True,
                                   invoke_args=[cfg.CONF, url],
                                   invoke_kwds=kwargs)
        return transport.Transport(mgr.driver)


    def test_call_engine_remote(self):
        if not 'executor' in cfg.CONF:
            cfg_grp = cfg.OptGroup(name='executor', title='Executor options')
            opts = [cfg.StrOpt('host', default='0.0.0.0'),
                    cfg.StrOpt('topic', default='executor')]
            cfg.CONF.register_group(cfg_grp)
            cfg.CONF.register_opts(opts, group=cfg_grp)

        transport = self._get_transport()
        target = messaging.Target(topic='executor', server='0.0.0.0')
        endpoints = [engine.EnginePool()]
        self.server = messaging.get_rpc_server(transport, target,
                                               endpoints, executor='eventlet')
        self.server.start()
        fake_ctx = {'user': 'admin','tenant': 'mistral'}
        ex_client = proxy.EnginePoolProxy(transport)

        id = ex_client.submit(fake_ctx)

        self.assertEqual(id, 0)
        time.sleep(2)
        ex_client.stop(fake_ctx, uid=id)

        self.server.stop()