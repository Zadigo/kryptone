import subprocess

from twisted.application.internet import TCPServer, TimerService
from twisted.application.service import Application
from twisted.cred.portal import Portal
from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.interfaces import IAddress
from twisted.internet.protocol import (ClientFactory, Factory, Protocol,
                                       ServerFactory)
from twisted.python import log
from twisted.web import server
from twisted.web.guard import BasicCredentialFactory, HTTPAuthSessionWrapper
from twisted.web.resource import WebSocketFactory, WebSocketProtocol
from twisted.web.static import File

# class BaseServer(Protocol):
#     def connectionMade(self):
#         self.transport.write(b'google')

#     def dataReceived(self, data):
#         print(data)


# class _Factory(Factory):
#     def buildProtocol(self, addr):
#         return BaseServer()


# if __name__ == '__main__':
#     endpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', 8123)
#     endpoint.connect(_Factory())
#     reactor.run()


class MyWebSocketProtocol(WebSocketProtocol):
    def onOpen(self):
        print("WebSocket connection opened")

    def onMessage(self, payload, isBinary):
        if not isBinary:
            message = payload.decode("utf-8")
            print(f"Received message: {message}")
            # Process the message as needed


resource = WebSocketFactory(MyWebSocketProtocol)
site = server.Site(resource)
reactor.listenTCP(8080, site)
reactor.run()
