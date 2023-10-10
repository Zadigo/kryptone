from twisted.internet.protocol import Factory, connectionDone
from twisted.python import failure
from kryptone import logger
from collections import defaultdict
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet import task


def something():
    print('Great')
    return False


class BaseProtocol(Protocol):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        pass

    def connectionLost(self, reason=None):
        pass

    def dataReceived(self, data):
        pass


class BaseFactory(Factory):
    default_protocol = BaseProtocol

    def __init__(self, reactor):
        self._reactor = reactor

    def buildProtocol(self, addr):
        # task_id = self._reactor.callLater(5, something)
        # task_id.cancel()

        # deferred = task.deferLater(self._reactor, 3, something)

        # def result(data):
        #     print(data)
        # deferred.addCallback(result)

        # def run_every_second():
        #     print('Loop runned')

        # def loop_done(data):
        #     print(data)
        #     self._reactor.stop()
        #     return True

        # def loop_failed(failure):
        #     print(failure)

        # loop = task.LoopingCall(run_every_second)
        # deferred_loop = loop.start(15)
        # deferred_loop.addCallback(loop_done)
        # deferred_loop.addErrback(loop_failed)

        return self.default_protocol(self)


def application(registry, spider_config, port=3459):
    logger.info('Starting TCP server...')
    endpoint = TCP4ServerEndpoint(reactor, port)
    logger.info(f'TCP server listening on port {port}')

    # spider_config.run()
    # registry.active_reactor = reactor
    endpoint.listen(BaseFactory(reactor))
    reactor.run()

    return reactor


# app = application()
