import eventlet

from mistral.openstack.common import log as logging

LOG = logging.getLogger(__name__)

class Engine(object):
    status = 'IDLE'
    stop_requested = False

    def __init__(self, uid):
        self.uid = uid


    def run(self):
        self.status = 'RUNNING'
        for i in range(1, 10):
            if self.stop_requested:
                self.status = 'STOPPED'
                print("Engine [%d] stopped." % self.uid)
                return
            print("Running engine [%d], count = %d..." % (self.uid, i))
            eventlet.sleep(1)
        self.status = "COMPLETE"
        print("Engine [%d] completed." % self.uid)

    def stop(self):
        self.stop_requested = True


class EnginePool(object):

    def __init__(self):
        LOG.info('Engine pool initialized...')
        self.pool = eventlet.GreenPool()
        self.engines = []


    def submit(self, ctx):
        '''
        Spawns a new execution, returns the ID immediately
        '''
        LOG.info("Run...")
        uid = len(self.engines)
        engine = Engine(uid)
        self.engines.append(engine)
        self.pool.spawn_n(engine.run)
        return uid

    def stop(self, ctx, uid):
        # stops an engine by ID
        LOG.info("Stopping engine %d" % uid)
        self.engines[uid].stop()

    def get(self, ctx, uid):
        LOG.info("Returning engine by id")
        return self.engines[uid]


