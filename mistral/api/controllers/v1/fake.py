from pecan import rest
from pecan import abort
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from mistral.api.controllers import resource
from mistral.engine.fake import proxy
from mistral.openstack.common import log as logging

LOG = logging.getLogger(__name__)

class Workbook(resource.Resource):
    name = wtypes.text
    description = wtypes.text
    tags = [wtypes.text]

class FakeExecutionController(rest.RestController):

    def __init__(self):
        transport = proxy.get_transport()
        self.engine_pool = proxy.EnginePoolProxy(transport)

    @wsme_pecan.wsexpose(wtypes.text, wtypes.text, int)
    def put(self, command, uid):
        LOG.debug("Update execution - ")
        LOG.debug("command %s uid %d" % (command, uid))
        # TODO: call stop the engine, by id, via proxy.
        if command == 'stop':
            self.engine_pool.stop({}, uid=uid)


    @wsme_pecan.wsexpose(int, body=Workbook, status_code=201)
    def post(self, workbook):
        LOG.debug("Create execution")
        fake_ctx = {'user': 'admin','tenant': 'mistral'}
        # TODO: pass a workbook to the execution...
        engine_id = self.engine_pool.submit(fake_ctx)
        return engine_id
