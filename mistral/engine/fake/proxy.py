from oslo import messaging
from oslo.config import cfg

from mistral.openstack.common import log as logging


LOG = logging.getLogger(__name__)

#FIXME: temporary hack to pass the transport around
_transport = None
def get_transport():
    global _transport
    if _transport is None:
        _transport = messaging.get_transport(cfg.CONF)
    return _transport

class EnginePoolProxy(object):
    def __init__(self, transport):
        """Construct an RPC proxy.

        :param transport: a messaging transport handle
        :type transport: Transport
        """
        target = messaging.Target(topic=cfg.CONF.executor.topic)
        self._client = messaging.RPCClient(transport, target)

    def submit(self, ctx, **kwargs):
        return self._client.call(ctx, 'submit', **kwargs)

    def stop(self, ctx, uid):
        return self._client.call(ctx, 'stop', uid=uid)
