import datetime
import signal

import pytz
from twisted.internet import interfaces, reactor
from twisted.internet.base import ThreadedResolver
from twisted.internet.defer import (Deferred, DeferredList, inlineCallbacks,
                                    maybeDeferred)
from twisted.internet.task import LoopingCall
# from twisted.utils.reactor import CallLaterOnce
from zope.interface.declarations import implementer


@implementer(interfaces.IResolverSimple)
class CachingThreadedResolver(ThreadedResolver):
    def __init__(self, reactor):
        super().__init__(reactor)

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.reactor}]>'

    @classmethod
    def new(cls, reactor):
        return cls(reactor)

    def prepare(self):
        self.reactor.installResolver(self)

    def getHostByName(self, name, **kwargs):
        return super().getHostByName(name, **kwargs)


def shutdown_handlers(func, override_signal_int=True):
    signal.signal(signal.SIGTERM, func)

    if signal.getsignal(signal.SIGINT) == signal.default_int_handler or override_signal_int:
        signal.signal(signal.SIGINT, func)

    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, func)


class ExecutionSlot:
    def __init__(self, next_call, scheduler):
        self.next_call = next_call
        self.scheduler = scheduler
        self.heartbeat = LoopingCall(next_call.schedule)


class ExcecutionEngineBackend:
    schedule_class = None

    def __init__(self, process_registry, spider_config):
        self.process_registry = process_registry
        self._spider_config = spider_config
        self.running = False
        self.paused = False
        self.start_time = datetime.datetime.now(tz=pytz.UTC)
        self.end_time = None
        self.execution_slot = None

    @inlineCallbacks
    def start(self):
        pass

    @inlineCallbacks
    def execute(self, spider_config):
        next_call = CallLaterOnce(self.next_request)
        self.execution_slot = ExecutionSlot(next_call, None)
        yield self.execute(spider_config)

    def next_request(self):
        pass

    def stop(self):
        pass

    def pause(self):
        pass

    def unpause(self):
        pass


# Crawler
class ProcessWrapper:
    execution_engine_class = ExcecutionEngineBackend

    def __init__(self, spider_config, registry):
        self._spider_config = spider_config
        self._registry = registry
        self.engine = registry.engine

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.spdider_config}]>'

    @inlineCallbacks
    def initialize(self):
        try:
            # self._spider_config.run()
            self.engine = self.execution_engine_class(
                self, self._spider_config)
            yield maybeDeferred(self.engine.start)
        except:
            pass


# CrawlerRunner
class ProcessRegistry:

    def __init__(self):
        self.spiders = []
        self.active_items = set()
        self.spider_configs = set()
        self.engine = None

    @inlineCallbacks
    def prepare_registry(self, spider_config):
        self.spider_configs.add(spider_config)

        instance = ProcessWrapper(spider_config, self)
        deferred_result = instance.initialize()
        self.active_items.add(deferred_result)

        def completed(result):
            return result
        return deferred_result.addBoth(completed)

    @inlineCallbacks
    def join_results(self):
        pass


class BaseProcess(ProcessRegistry):
    def __init__(self):
        self.spider = None
        self.engine = None
        self.intialized = False
        super().__init__()

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.spider}] >'

    def _shutdown(self, *args, **kwargs):
        # _signal_shutdown
        shutdown_handlers(self._shutdown)

    def _kill(self):
        shutdown_handlers(signal.SIG_IGN)
        reactor.callFromThread(self._stop_reactor)

    def _stop_reactor(self):
        try:
            reactor.stop()
        except RuntimeError:
            pass

    def stop(self):
        return DeferredList([spider.stop() for spider in self.spider_configs])

    def start(self, spider_config=None, override_signal_int=True):
        reactor._handleSignals()
        shutdown_handlers(self._shutdown)

        resolver = CachingThreadedResolver.new(reactor)
        resolver.prepare()

        thread_pool = reactor.getThreadPool()
        thread_pool.adjustPoolsize(maxthreads=10)
        deferred_result = self.prepare_registry(spider_config)

        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)
        # reactor.run(installSignalHandlers=False)


# process = BaseProcess()
# process.start()


# cmline [execute] -> CrawlerProcess -> CrawlerRunner._get_spider_loader ->
# Command.run -> CrawlerProcess.crawl (CrawlerRunner.create_crawler [returns Crawler] -> CrawlerRunner._crawl -> Crawler.crawl)
# -> CrawlerProcess.start
